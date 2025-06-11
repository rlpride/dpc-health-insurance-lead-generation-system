#!/usr/bin/env python3
"""Monitor Pipedrive CRM integration status and performance."""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.live import Live

from api.pipedrive import PipedriveIntegrationService
from config.settings import get_settings
from models.company import Company
from models.contact import Contact

console = Console()
logger = logging.getLogger(__name__)


class PipedriveMonitor:
    """Monitor for Pipedrive CRM integration."""
    
    def __init__(self):
        """Initialize the monitor."""
        self.settings = get_settings()
        
        # Database setup
        self.engine = create_engine(str(self.settings.database_url))
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def get_sync_overview(self) -> Dict[str, Any]:
        """Get comprehensive sync overview."""
        db = self.SessionLocal()
        
        try:
            # Company statistics
            company_stats = db.execute(text("""
                SELECT 
                    crm_sync_status,
                    COUNT(*) as count,
                    AVG(lead_score) as avg_score,
                    MIN(created_at) as oldest,
                    MAX(updated_at) as newest
                FROM companies 
                GROUP BY crm_sync_status
            """)).fetchall()
            
            # Contact statistics
            contact_stats = db.execute(text("""
                SELECT 
                    crm_sync_status,
                    COUNT(*) as count,
                    COUNT(CASE WHEN is_decision_maker = true THEN 1 END) as decision_makers
                FROM contacts 
                GROUP BY crm_sync_status
            """)).fetchall()
            
            # High-scoring leads
            high_score_stats = db.execute(text(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN crm_sync_status = 'synced' THEN 1 END) as synced,
                    COUNT(CASE WHEN crm_sync_status = 'pending' THEN 1 END) as pending,
                    COUNT(CASE WHEN crm_sync_status = 'failed' THEN 1 END) as failed
                FROM companies 
                WHERE lead_score >= {self.settings.high_score_threshold}
            """)).fetchone()
            
            # Recent activity
            recent_syncs = db.execute(text("""
                SELECT 
                    name,
                    lead_score,
                    crm_sync_status,
                    updated_at,
                    pipedrive_id
                FROM companies 
                WHERE crm_sync_status IN ('synced', 'failed')
                ORDER BY updated_at DESC 
                LIMIT 10
            """)).fetchall()
            
            # Performance metrics
            sync_performance = db.execute(text("""
                SELECT 
                    DATE(updated_at) as sync_date,
                    COUNT(*) as synced_count,
                    AVG(lead_score) as avg_score
                FROM companies 
                WHERE crm_sync_status = 'synced' 
                    AND updated_at >= NOW() - INTERVAL '7 days'
                GROUP BY DATE(updated_at)
                ORDER BY sync_date DESC
            """)).fetchall()
            
            return {
                'company_stats': [dict(row._mapping) for row in company_stats],
                'contact_stats': [dict(row._mapping) for row in contact_stats],
                'high_score_stats': dict(high_score_stats._mapping) if high_score_stats else {},
                'recent_syncs': [dict(row._mapping) for row in recent_syncs],
                'sync_performance': [dict(row._mapping) for row in sync_performance],
                'timestamp': datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()
    
    def create_dashboard(self) -> Layout:
        """Create a rich dashboard layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        return layout
    
    def update_dashboard(self, layout: Layout, data: Dict[str, Any]):
        """Update dashboard with current data."""
        # Header
        layout["header"].update(
            Panel(
                f"[bold blue]Pipedrive CRM Integration Monitor[/bold blue]\n"
                f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                title="DPC Health Insurance Lead Generation System"
            )
        )
        
        # Company sync status table
        company_table = Table(title="Company Sync Status")
        company_table.add_column("Status", style="cyan")
        company_table.add_column("Count", justify="right", style="green")
        company_table.add_column("Avg Score", justify="right", style="yellow")
        company_table.add_column("Oldest", style="dim")
        
        for stat in data['company_stats']:
            oldest = stat['oldest'].strftime('%Y-%m-%d') if stat['oldest'] else 'N/A'
            avg_score = f"{stat['avg_score']:.1f}" if stat['avg_score'] else 'N/A'
            company_table.add_row(
                stat['crm_sync_status'],
                str(stat['count']),
                avg_score,
                oldest
            )
        
        # Contact sync status table
        contact_table = Table(title="Contact Sync Status")
        contact_table.add_column("Status", style="cyan")
        contact_table.add_column("Count", justify="right", style="green")
        contact_table.add_column("Decision Makers", justify="right", style="yellow")
        
        for stat in data['contact_stats']:
            contact_table.add_row(
                stat['crm_sync_status'],
                str(stat['count']),
                str(stat['decision_makers'])
            )
        
        layout["left"].split_column(company_table, contact_table)
        
        # High-score leads panel
        high_score = data['high_score_stats']
        high_score_panel = Panel(
            f"Total: [bold]{high_score.get('total', 0)}[/bold]\n"
            f"Synced: [green]{high_score.get('synced', 0)}[/green]\n"
            f"Pending: [yellow]{high_score.get('pending', 0)}[/yellow]\n"
            f"Failed: [red]{high_score.get('failed', 0)}[/red]",
            title=f"High-Score Leads (≥{self.settings.high_score_threshold})"
        )
        
        # Recent activity table
        recent_table = Table(title="Recent Sync Activity")
        recent_table.add_column("Company", style="cyan", max_width=30)
        recent_table.add_column("Score", justify="right", style="yellow")
        recent_table.add_column("Status", style="green")
        recent_table.add_column("Updated", style="dim")
        
        for sync in data['recent_syncs'][:5]:
            status_color = "green" if sync['crm_sync_status'] == 'synced' else "red"
            recent_table.add_row(
                sync['name'][:30] + "..." if len(sync['name']) > 30 else sync['name'],
                str(sync['lead_score']),
                f"[{status_color}]{sync['crm_sync_status']}[/{status_color}]",
                sync['updated_at'].strftime('%m-%d %H:%M')
            )
        
        layout["right"].split_column(high_score_panel, recent_table)
        
        # Footer with performance summary
        perf_data = data['sync_performance']
        if perf_data:
            total_synced = sum(p['synced_count'] for p in perf_data)
            avg_daily = total_synced / len(perf_data) if perf_data else 0
            footer_text = f"7-Day Performance: {total_synced} synced | {avg_daily:.1f} per day avg"
        else:
            footer_text = "No recent sync activity"
        
        layout["footer"].update(
            Panel(footer_text, title="Performance Summary")
        )
    
    async def monitor_continuous(self, refresh_seconds: int = 30):
        """Run continuous monitoring with live dashboard."""
        layout = self.create_dashboard()
        
        with Live(layout, refresh_per_second=1) as live:
            while True:
                try:
                    data = self.get_sync_overview()
                    self.update_dashboard(layout, data)
                    
                    await asyncio.sleep(refresh_seconds)
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Monitoring stopped by user[/yellow]")
                    break
                except Exception as e:
                    console.print(f"[red]Monitor error: {e}[/red]")
                    await asyncio.sleep(5)
    
    def print_summary_report(self):
        """Print a comprehensive summary report."""
        data = self.get_sync_overview()
        
        console.print("\n[bold blue]Pipedrive CRM Integration Report[/bold blue]")
        console.print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Company statistics
        console.print("[bold]Company Sync Status:[/bold]")
        for stat in data['company_stats']:
            status = stat['crm_sync_status']
            count = stat['count']
            avg_score = stat['avg_score'] or 0
            
            status_color = {
                'synced': 'green',
                'pending': 'yellow', 
                'failed': 'red'
            }.get(status, 'white')
            
            console.print(f"  [{status_color}]{status}[/{status_color}]: {count} companies (avg score: {avg_score:.1f})")
        
        # High-score summary
        high_score = data['high_score_stats']
        console.print(f"\n[bold]High-Score Leads (≥{self.settings.high_score_threshold}):[/bold]")
        console.print(f"  Total: {high_score.get('total', 0)}")
        console.print(f"  [green]Synced: {high_score.get('synced', 0)}[/green]")
        console.print(f"  [yellow]Pending: {high_score.get('pending', 0)}[/yellow]")
        console.print(f"  [red]Failed: {high_score.get('failed', 0)}[/red]")
        
        # Contact statistics
        console.print(f"\n[bold]Contact Sync Status:[/bold]")
        for stat in data['contact_stats']:
            status = stat['crm_sync_status']
            count = stat['count']
            decision_makers = stat['decision_makers']
            
            status_color = {
                'synced': 'green',
                'pending': 'yellow',
                'failed': 'red'
            }.get(status, 'white')
            
            console.print(f"  [{status_color}]{status}[/{status_color}]: {count} contacts ({decision_makers} decision makers)")
        
        # Performance trend
        if data['sync_performance']:
            console.print(f"\n[bold]Recent Performance (7 days):[/bold]")
            for perf in data['sync_performance'][:5]:
                console.print(f"  {perf['sync_date']}: {perf['synced_count']} synced (avg score: {perf['avg_score']:.1f})")
    
    async def check_sync_health(self) -> Dict[str, Any]:
        """Check the health of the sync process."""
        db = self.SessionLocal()
        
        try:
            health_issues = []
            recommendations = []
            
            # Check for old pending records
            old_pending = db.query(Company).filter(
                Company.crm_sync_status == 'pending',
                Company.created_at < datetime.utcnow() - timedelta(days=7)
            ).count()
            
            if old_pending > 0:
                health_issues.append(f"{old_pending} companies pending sync for >7 days")
                recommendations.append("Consider manual sync or investigating failed connections")
            
            # Check failed sync rate
            total_companies = db.query(Company).count()
            failed_companies = db.query(Company).filter(Company.crm_sync_status == 'failed').count()
            
            if total_companies > 0:
                failed_rate = (failed_companies / total_companies) * 100
                if failed_rate > 10:
                    health_issues.append(f"High failure rate: {failed_rate:.1f}% of companies failed to sync")
                    recommendations.append("Review error logs and API connectivity")
            
            # Check high-score leads not synced
            high_score_pending = db.query(Company).filter(
                Company.lead_score >= self.settings.high_score_threshold,
                Company.crm_sync_status == 'pending'
            ).count()
            
            if high_score_pending > 5:
                health_issues.append(f"{high_score_pending} high-score leads awaiting sync")
                recommendations.append("Prioritize high-score lead sync with --high-priority-only flag")
            
            # Overall health status
            health_status = "HEALTHY" if not health_issues else "NEEDS_ATTENTION"
            
            return {
                'status': health_status,
                'issues': health_issues,
                'recommendations': recommendations,
                'metrics': {
                    'old_pending': old_pending,
                    'failed_rate': failed_rate if total_companies > 0 else 0,
                    'high_score_pending': high_score_pending
                }
            }
            
        finally:
            db.close()


async def main():
    """Main monitoring function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor Pipedrive CRM integration")
    parser.add_argument('--mode', choices=['dashboard', 'report', 'health'], default='report',
                       help='Monitoring mode')
    parser.add_argument('--refresh', type=int, default=30,
                       help='Dashboard refresh interval in seconds')
    parser.add_argument('--output', choices=['console', 'json'], default='console',
                       help='Output format')
    
    args = parser.parse_args()
    
    monitor = PipedriveMonitor()
    
    if args.mode == 'dashboard':
        await monitor.monitor_continuous(args.refresh)
    elif args.mode == 'report':
        if args.output == 'json':
            data = monitor.get_sync_overview()
            print(json.dumps(data, indent=2, default=str))
        else:
            monitor.print_summary_report()
    elif args.mode == 'health':
        health = await monitor.check_sync_health()
        if args.output == 'json':
            print(json.dumps(health, indent=2))
        else:
            console.print(f"\n[bold]Sync Health Status: {health['status']}[/bold]")
            
            if health['issues']:
                console.print("\n[red]Issues Found:[/red]")
                for issue in health['issues']:
                    console.print(f"  • {issue}")
            
            if health['recommendations']:
                console.print("\n[yellow]Recommendations:[/yellow]")
                for rec in health['recommendations']:
                    console.print(f"  • {rec}")
            
            if not health['issues']:
                console.print("\n[green]✓ All systems operating normally[/green]")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())