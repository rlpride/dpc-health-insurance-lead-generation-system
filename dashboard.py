"""Flask Dashboard for DPC Health Insurance Lead Generation System

Real-time monitoring dashboard displaying:
- Lead generation metrics
- API usage and costs
- Error rates and system health
- Queue depths and processing times
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Any, Optional
import json
import redis
import pika
from flask import Flask, render_template, jsonify, request
import plotly.graph_objs as go
import plotly.utils
from sqlalchemy import func, desc, and_, or_
from sqlalchemy.orm import sessionmaker

from models import (
    get_db_session, Company, Contact, ScrapingLog, 
    ApiUsage, LeadScore, engine
)
from config.settings import Settings

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Load settings
settings = Settings()

# Initialize Redis connection for queue monitoring
try:
    redis_client = redis.from_url(str(settings.redis_url))
except Exception:
    redis_client = None

class DashboardService:
    """Service class for dashboard data operations."""
    
    @staticmethod
    def get_lead_generation_metrics(days: int = 7) -> Dict[str, Any]:
        """Get lead generation metrics for the specified number of days."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        with get_db_session() as db:
            # Total companies and contacts
            total_companies = db.query(Company).count()
            total_contacts = db.query(Contact).count()
            
            # Recent activity
            recent_companies = db.query(Company).filter(
                Company.created_at >= start_date
            ).count()
            
            recent_contacts = db.query(Contact).filter(
                Contact.created_at >= start_date
            ).count()
            
            # Lead scores distribution
            score_distribution = db.query(
                func.case(
                    (Company.lead_score >= 80, 'High (80+)'),
                    (Company.lead_score >= 60, 'Medium (60-79)'),
                    (Company.lead_score >= 40, 'Low (40-59)'),
                    else_='Very Low (<40)'
                ).label('score_range'),
                func.count(Company.id).label('count')
            ).filter(Company.lead_score.isnot(None)).group_by(
                func.case(
                    (Company.lead_score >= 80, 'High (80+)'),
                    (Company.lead_score >= 60, 'Medium (60-79)'),
                    (Company.lead_score >= 40, 'Low (40-59)'),
                    else_='Very Low (<40)'
                )
            ).all()
            
            # Daily trend
            daily_trend = db.query(
                func.date(Company.created_at).label('date'),
                func.count(Company.id).label('companies'),
                func.count(Contact.id).label('contacts')
            ).outerjoin(Contact).filter(
                Company.created_at >= start_date
            ).group_by(func.date(Company.created_at)).all()
            
            # Top performing states
            top_states = db.query(
                Company.state,
                func.count(Company.id).label('count'),
                func.avg(Company.lead_score).label('avg_score')
            ).filter(
                Company.state.isnot(None),
                Company.lead_score.isnot(None)
            ).group_by(Company.state).order_by(
                desc(func.count(Company.id))
            ).limit(10).all()
            
            return {
                'totals': {
                    'companies': total_companies,
                    'contacts': total_contacts,
                    'recent_companies': recent_companies,
                    'recent_contacts': recent_contacts
                },
                'score_distribution': [
                    {'range': row.score_range, 'count': row.count}
                    for row in score_distribution
                ],
                'daily_trend': [
                    {
                        'date': row.date.isoformat(),
                        'companies': row.companies,
                        'contacts': row.contacts or 0
                    }
                    for row in daily_trend
                ],
                'top_states': [
                    {
                        'state': row.state,
                        'count': row.count,
                        'avg_score': float(row.avg_score) if row.avg_score else 0
                    }
                    for row in top_states
                ]
            }
    
    @staticmethod
    def get_api_usage_metrics(days: int = 30) -> Dict[str, Any]:
        """Get API usage and cost metrics."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        with get_db_session() as db:
            # Total costs and usage
            total_cost = db.query(
                func.sum(ApiUsage.total_cost)
            ).filter(
                ApiUsage.created_at >= start_date
            ).scalar() or 0
            
            total_requests = db.query(ApiUsage).filter(
                ApiUsage.created_at >= start_date
            ).count()
            
            # Usage by provider
            provider_usage = db.query(
                ApiUsage.provider,
                func.count(ApiUsage.id).label('requests'),
                func.sum(ApiUsage.total_cost).label('cost'),
                func.sum(ApiUsage.credits_used).label('credits'),
                func.avg(ApiUsage.response_time_ms).label('avg_response_time')
            ).filter(
                ApiUsage.created_at >= start_date
            ).group_by(ApiUsage.provider).all()
            
            # Daily cost trend
            daily_costs = db.query(
                func.date(ApiUsage.created_at).label('date'),
                ApiUsage.provider,
                func.sum(ApiUsage.total_cost).label('cost'),
                func.count(ApiUsage.id).label('requests')
            ).filter(
                ApiUsage.created_at >= start_date
            ).group_by(
                func.date(ApiUsage.created_at),
                ApiUsage.provider
            ).all()
            
            # Success rate by provider
            success_rates = db.query(
                ApiUsage.provider,
                func.count(ApiUsage.id).label('total'),
                func.sum(func.case(
                    (ApiUsage.success == True, 1),
                    else_=0
                )).label('successful')
            ).filter(
                ApiUsage.created_at >= start_date
            ).group_by(ApiUsage.provider).all()
            
            # Monthly limits check
            current_month = datetime.utcnow().strftime("%Y-%m")
            monthly_usage = db.query(
                ApiUsage.provider,
                func.count(ApiUsage.id).label('requests'),
                func.sum(ApiUsage.total_cost).label('cost')
            ).filter(
                ApiUsage.month == current_month
            ).group_by(ApiUsage.provider).all()
            
            return {
                'totals': {
                    'cost': float(total_cost),
                    'requests': total_requests
                },
                'provider_usage': [
                    {
                        'provider': row.provider,
                        'requests': row.requests,
                        'cost': float(row.cost or 0),
                        'credits': row.credits or 0,
                        'avg_response_time': float(row.avg_response_time or 0)
                    }
                    for row in provider_usage
                ],
                'daily_costs': [
                    {
                        'date': row.date.isoformat(),
                        'provider': row.provider,
                        'cost': float(row.cost or 0),
                        'requests': row.requests
                    }
                    for row in daily_costs
                ],
                'success_rates': [
                    {
                        'provider': row.provider,
                        'success_rate': (row.successful / row.total * 100) if row.total > 0 else 0,
                        'total': row.total,
                        'successful': row.successful
                    }
                    for row in success_rates
                ],
                'monthly_usage': [
                    {
                        'provider': row.provider,
                        'requests': row.requests,
                        'cost': float(row.cost or 0)
                    }
                    for row in monthly_usage
                ]
            }
    
    @staticmethod
    def get_system_health_metrics() -> Dict[str, Any]:
        """Get system health and error rate metrics."""
        with get_db_session() as db:
            # Recent scraping operations
            recent_scraping = db.query(ScrapingLog).filter(
                ScrapingLog.started_at >= datetime.utcnow() - timedelta(hours=24)
            ).order_by(desc(ScrapingLog.started_at)).limit(20).all()
            
            # Error rates by source
            error_rates = db.query(
                ScrapingLog.source,
                func.count(ScrapingLog.id).label('total'),
                func.sum(func.case(
                    (ScrapingLog.status == 'failed', 1),
                    else_=0
                )).label('failures')
            ).filter(
                ScrapingLog.started_at >= datetime.utcnow() - timedelta(days=7)
            ).group_by(ScrapingLog.source).all()
            
            # API error rates
            api_errors = db.query(
                ApiUsage.provider,
                func.count(ApiUsage.id).label('total'),
                func.sum(func.case(
                    (ApiUsage.success == False, 1),
                    else_=0
                )).label('failures')
            ).filter(
                ApiUsage.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).group_by(ApiUsage.provider).all()
            
            # Processing performance
            avg_processing_times = db.query(
                ScrapingLog.source,
                func.avg(ScrapingLog.duration_seconds).label('avg_duration'),
                func.avg(ScrapingLog.records_processed).label('avg_records')
            ).filter(
                ScrapingLog.status == 'success',
                ScrapingLog.started_at >= datetime.utcnow() - timedelta(days=7)
            ).group_by(ScrapingLog.source).all()
            
            return {
                'recent_operations': [
                    {
                        'id': str(log.id),
                        'source': log.source,
                        'status': log.status,
                        'records_processed': log.records_processed or 0,
                        'duration': log.duration_seconds or 0,
                        'started_at': log.started_at.isoformat() if log.started_at else None,
                        'error_message': log.error_message
                    }
                    for log in recent_scraping
                ],
                'scraping_error_rates': [
                    {
                        'source': row.source,
                        'error_rate': (row.failures / row.total * 100) if row.total > 0 else 0,
                        'total': row.total,
                        'failures': row.failures
                    }
                    for row in error_rates
                ],
                'api_error_rates': [
                    {
                        'provider': row.provider,
                        'error_rate': (row.failures / row.total * 100) if row.total > 0 else 0,
                        'total': row.total,
                        'failures': row.failures
                    }
                    for row in api_errors
                ],
                'processing_performance': [
                    {
                        'source': row.source,
                        'avg_duration': float(row.avg_duration or 0),
                        'avg_records': float(row.avg_records or 0)
                    }
                    for row in avg_processing_times
                ]
            }
    
    @staticmethod
    def get_queue_metrics() -> Dict[str, Any]:
        """Get queue depths and processing metrics."""
        metrics = {
            'queue_depths': {},
            'processing_rates': {}
        }
        
        # Try to get Redis queue information
        if redis_client:
            try:
                # Get queue lengths from Redis
                queue_names = [
                    'collection_queue',
                    'enrichment_queue', 
                    'processing_queue',
                    'scoring_queue'
                ]
                
                for queue_name in queue_names:
                    depth = redis_client.llen(queue_name)
                    metrics['queue_depths'][queue_name] = depth
                    
            except Exception as e:
                print(f"Error getting Redis metrics: {e}")
        
        # Get processing rates from database
        with get_db_session() as db:
            # Recent processing activity
            recent_activity = db.query(
                func.date_trunc('hour', ScrapingLog.started_at).label('hour'),
                func.count(ScrapingLog.id).label('operations'),
                func.sum(ScrapingLog.records_processed).label('records')
            ).filter(
                ScrapingLog.started_at >= datetime.utcnow() - timedelta(hours=24)
            ).group_by(
                func.date_trunc('hour', ScrapingLog.started_at)
            ).all()
            
            metrics['processing_rates'] = [
                {
                    'hour': row.hour.isoformat() if row.hour else None,
                    'operations': row.operations,
                    'records': row.records or 0
                }
                for row in recent_activity
            ]
        
        return metrics

# Dashboard routes
@app.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    try:
        # Check database connection
        with get_db_session() as db:
            db.execute("SELECT 1")
        
        # Check Redis connection (optional)
        redis_status = "unavailable"
        if redis_client:
            try:
                redis_client.ping()
                redis_status = "connected"
            except Exception:
                redis_status = "error"
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "connected",
                "redis": redis_status
            },
            "version": "1.0.0"
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }), 503

@app.route('/api/metrics/leads')
def api_lead_metrics():
    """API endpoint for lead generation metrics."""
    try:
        days = request.args.get('days', default=7, type=int)
        if days < 1 or days > 365:
            return jsonify({"error": "Days parameter must be between 1 and 365"}), 400
        
        metrics = DashboardService.get_lead_generation_metrics(days)
        return jsonify(metrics)
    except Exception as e:
        app.logger.error(f"Error getting lead metrics: {e}")
        return jsonify({"error": "Failed to retrieve lead metrics"}), 500

@app.route('/api/metrics/api-usage')
def api_usage_metrics():
    """API endpoint for API usage metrics."""
    try:
        days = request.args.get('days', default=30, type=int)
        if days < 1 or days > 365:
            return jsonify({"error": "Days parameter must be between 1 and 365"}), 400
        
        metrics = DashboardService.get_api_usage_metrics(days)
        return jsonify(metrics)
    except Exception as e:
        app.logger.error(f"Error getting API usage metrics: {e}")
        return jsonify({"error": "Failed to retrieve API usage metrics"}), 500

@app.route('/api/metrics/system-health')
def api_system_health():
    """API endpoint for system health metrics."""
    try:
        metrics = DashboardService.get_system_health_metrics()
        return jsonify(metrics)
    except Exception as e:
        app.logger.error(f"Error getting system health metrics: {e}")
        return jsonify({"error": "Failed to retrieve system health metrics"}), 500

@app.route('/api/metrics/queues')
def api_queue_metrics():
    """API endpoint for queue metrics."""
    try:
        metrics = DashboardService.get_queue_metrics()
        return jsonify(metrics)
    except Exception as e:
        app.logger.error(f"Error getting queue metrics: {e}")
        return jsonify({"error": "Failed to retrieve queue metrics"}), 500

@app.route('/api/charts/leads-trend')
def chart_leads_trend():
    """Generate leads trend chart data."""
    try:
        days = request.args.get('days', default=7, type=int)
        if days < 1 or days > 365:
            return jsonify({"error": "Days parameter must be between 1 and 365"}), 400
        
        metrics = DashboardService.get_lead_generation_metrics(days)
        
        dates = [item['date'] for item in metrics['daily_trend']]
        companies = [item['companies'] for item in metrics['daily_trend']]
        contacts = [item['contacts'] for item in metrics['daily_trend']]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=companies,
            mode='lines+markers',
            name='Companies',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=8)
        ))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=contacts,
            mode='lines+markers',
            name='Contacts',
            line=dict(color='#ff7f0e', width=3),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title='Daily Lead Generation Trend',
            xaxis_title='Date',
            yaxis_title='Count',
            hovermode='x unified',
            template='plotly_white'
        )
        
        return jsonify(json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig)))
    except Exception as e:
        app.logger.error(f"Error generating leads trend chart: {e}")
        return jsonify({"error": "Failed to generate chart"}), 500

@app.route('/api/charts/score-distribution')
def chart_score_distribution():
    """Generate lead score distribution chart."""
    try:
        metrics = DashboardService.get_lead_generation_metrics()
        
        ranges = [item['range'] for item in metrics['score_distribution']]
        counts = [item['count'] for item in metrics['score_distribution']]
        
        colors = ['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4']  # Red to Blue
        
        fig = go.Figure(data=[
            go.Bar(
                x=ranges,
                y=counts,
                marker_color=colors[:len(ranges)]
            )
        ])
        
        fig.update_layout(
            title='Lead Score Distribution',
            xaxis_title='Score Range',
            yaxis_title='Number of Companies',
            template='plotly_white'
        )
        
        return jsonify(json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig)))
    except Exception as e:
        app.logger.error(f"Error generating score distribution chart: {e}")
        return jsonify({"error": "Failed to generate chart"}), 500

@app.route('/api/charts/api-costs')
def chart_api_costs():
    """Generate API costs breakdown chart."""
    try:
        metrics = DashboardService.get_api_usage_metrics()
        
        providers = [item['provider'] for item in metrics['provider_usage']]
        costs = [item['cost'] for item in metrics['provider_usage']]
        
        if not providers or not any(costs):
            # Return empty chart if no data
            fig = go.Figure()
            fig.add_annotation(
                text="No API cost data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=16)
            )
            fig.update_layout(
                title='API Costs by Provider',
                template='plotly_white'
            )
        else:
            fig = go.Figure(data=[
                go.Pie(
                    labels=providers,
                    values=costs,
                    hole=0.3
                )
            ])
            
            fig.update_layout(
                title='API Costs by Provider',
                template='plotly_white'
            )
        
        return jsonify(json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig)))
    except Exception as e:
        app.logger.error(f"Error generating API costs chart: {e}")
        return jsonify({"error": "Failed to generate chart"}), 500

@app.route('/api/charts/error-rates')
def chart_error_rates():
    """Generate error rates chart."""
    try:
        metrics = DashboardService.get_system_health_metrics()
        
        # Combine scraping and API error rates
        scraping_sources = [item['source'] for item in metrics['scraping_error_rates']]
        scraping_rates = [item['error_rate'] for item in metrics['scraping_error_rates']]
        
        api_providers = [item['provider'] for item in metrics['api_error_rates']]
        api_rates = [item['error_rate'] for item in metrics['api_error_rates']]
        
        fig = go.Figure()
        
        if scraping_sources:
            fig.add_trace(go.Bar(
                name='Scraping Errors',
                x=scraping_sources,
                y=scraping_rates,
                marker_color='#ff7f0e'
            ))
        
        if api_providers:
            fig.add_trace(go.Bar(
                name='API Errors',
                x=api_providers,
                y=api_rates,
                marker_color='#d62728'
            ))
        
        if not scraping_sources and not api_providers:
            fig.add_annotation(
                text="No error data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=16)
            )
        
        fig.update_layout(
            title='Error Rates by Source/Provider',
            xaxis_title='Source/Provider',
            yaxis_title='Error Rate (%)',
            barmode='group',
            template='plotly_white'
        )
        
        return jsonify(json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig)))
    except Exception as e:
        app.logger.error(f"Error generating error rates chart: {e}")
        return jsonify({"error": "Failed to generate chart"}), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    app.logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle uncaught exceptions."""
    app.logger.error(f"Unhandled exception: {e}")
    return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)