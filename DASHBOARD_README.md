# Lead Generation Dashboard

A comprehensive real-time monitoring dashboard for the DPC Health Insurance Lead Generation System, built with Flask and Plotly.

## 🚀 Features

### 📊 Real-time Metrics
- **Lead Generation Tracking**: Monitor total companies and contacts collected
- **Daily Trends**: Track lead generation progress over time
- **Lead Score Distribution**: Visualize quality of leads by scoring ranges

### 💰 API Usage & Cost Monitoring
- **Cost Breakdown**: Track API costs by provider (Apollo, Proxycurl, Dropcontact)
- **Usage Analytics**: Monitor API request volumes and response times
- **Monthly Limits**: Track usage against monthly API limits
- **Success Rates**: Monitor API reliability and error rates

### 🏥 System Health Monitoring
- **Error Rates**: Track scraping and API errors by source
- **Processing Performance**: Monitor operation duration and throughput
- **Recent Operations**: View latest scraping activities and their status
- **System Status**: Overall health indicators with color-coded alerts

### 📋 Queue Management
- **Queue Depths**: Monitor processing queue backlogs
- **Processing Rates**: Track hourly processing volumes
- **Bottleneck Detection**: Identify performance bottlenecks

### 🎨 Interactive Visualizations
- **Plotly Charts**: Interactive, responsive charts with hover details
- **Real-time Updates**: Auto-refresh every 30 seconds
- **Mobile Responsive**: Works on desktop, tablet, and mobile devices

## 🛠️ Installation

### Quick Start (Standalone)

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp env.example .env
   # Edit .env with your database and API credentials
   ```

3. **Run Dashboard**
   ```bash
   python run_dashboard.py
   ```

4. **Access Dashboard**
   Open http://localhost:5000 in your browser

### Docker Setup

1. **Build and Run with Docker Compose**
   ```bash
   docker-compose up dashboard
   ```

2. **Access Dashboard**
   Open http://localhost:5000 in your browser

### Production Deployment

1. **Run in Production Mode**
   ```bash
   python run_dashboard.py --production --host 0.0.0.0 --port 8080
   ```

2. **Using Docker in Production**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d dashboard
   ```

## 📋 Requirements

### System Requirements
- Python 3.9+
- PostgreSQL database with lead generation data
- Redis (optional, for queue monitoring)
- 2GB RAM minimum, 4GB recommended

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/lead_generation

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# API Keys (for cost tracking)
APOLLO_API_KEY=your_apollo_key
PROXYCURL_API_KEY=your_proxycurl_key
DROPCONTACT_API_KEY=your_dropcontact_key

# Dashboard Settings
ENV=production
DEBUG=False
SECRET_KEY=your_secret_key_here
```

## 🎯 Usage

### Dashboard Sections

#### 1. Key Metrics Cards
- **Total Companies**: Count of all companies in database
- **Total Contacts**: Count of all contact records
- **Monthly API Costs**: Current month's API spending
- **System Health**: Overall system status indicator

#### 2. Lead Generation Trends
- Line chart showing daily company and contact acquisition
- Adjustable time range (7, 14, 30 days)
- Hover for detailed daily statistics

#### 3. Lead Score Distribution
- Bar chart showing quality distribution of leads
- Color-coded ranges: High (80+), Medium (60-79), Low (40-59), Very Low (<40)

#### 4. API Usage & Costs
- Pie chart showing cost breakdown by provider
- Monthly usage tracking against limits
- Cost per request analysis

#### 5. Error Rates
- Grouped bar chart showing error rates by source/provider
- Separate tracking for scraping vs API errors
- 7-day rolling average

#### 6. Queue Status
- Real-time queue depth monitoring
- Color-coded alerts: Green (<500), Yellow (500-1000), Red (>1000)
- Processing rate visualization

#### 7. Recent Operations
- Table of latest scraping operations
- Status indicators and error messages
- Performance metrics (duration, records processed)

#### 8. API Provider Performance
- Detailed table of API provider statistics
- Success rates, response times, costs
- Health status indicators

### Navigation Features

- **Auto-refresh**: Dashboard updates every 30 seconds
- **Manual Refresh**: Click refresh button or press Ctrl+R
- **Responsive Design**: Adapts to screen size
- **Pause/Resume**: Auto-refresh pauses when tab is hidden

## 🔧 Configuration

### Dashboard Settings
```python
# dashboard.py
app.config.update({
    'SECRET_KEY': 'your_secret_key',
    'DEBUG': False,  # Set to True for development
    'TEMPLATES_AUTO_RELOAD': True,
})
```

### Refresh Intervals
```javascript
// Modify in templates/dashboard.html
refreshInterval = setInterval(refreshAllData, 30000);  // 30 seconds
```

### Chart Customization
```python
# Modify chart colors and styles in dashboard.py
colors = ['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4']
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Dashboard Won't Start
```bash
# Check dependencies
python run_dashboard.py --skip-checks

# Verify database connection
python -c "from models import get_db_session; get_db_session()"
```

#### 2. No Data Showing
- Ensure lead generation system has run and populated database
- Check database connection in browser console
- Verify API endpoints return data: http://localhost:5000/api/metrics/leads

#### 3. Charts Not Loading
- Check browser console for JavaScript errors
- Verify Plotly.js is loading from CDN
- Clear browser cache and reload

#### 4. Redis Connection Issues
- Queue monitoring will show "No queue data available"
- Dashboard will function without Redis
- Check Redis URL in environment variables

#### 5. Performance Issues
- Reduce refresh interval for large datasets
- Add database indexes for better query performance
- Consider pagination for large result sets

### Debug Mode
```bash
# Run with debug logging
python run_dashboard.py --debug
```

### Health Checks
```bash
# Test API endpoints
curl http://localhost:5000/api/metrics/leads
curl http://localhost:5000/api/metrics/system-health
curl http://localhost:5000/api/metrics/queues
```

## 🏗️ Architecture

### Technology Stack
- **Backend**: Flask (Python web framework)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis (optional)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Charts**: Plotly.js
- **Styling**: Bootstrap 5 + Custom CSS
- **Icons**: Font Awesome

### Data Flow
```
Database → SQLAlchemy Models → Flask Routes → JSON API → JavaScript → Plotly Charts
```

### API Endpoints
- `GET /` - Dashboard HTML page
- `GET /api/metrics/leads` - Lead generation metrics
- `GET /api/metrics/api-usage` - API usage and costs
- `GET /api/metrics/system-health` - System health data
- `GET /api/metrics/queues` - Queue status
- `GET /api/charts/*` - Chart data endpoints

## 🔒 Security

### Production Security
- Set strong SECRET_KEY
- Use HTTPS in production
- Implement authentication if needed
- Restrict network access to dashboard port
- Keep dependencies updated

### Environment Security
```bash
# Secure environment variables
chmod 600 .env
```

## 📈 Performance Optimization

### Database Optimization
- Add indexes on frequently queried columns
- Use connection pooling
- Implement query result caching

### Frontend Optimization
- Enable compression (gzip)
- Use CDN for static assets
- Implement lazy loading for charts
- Add browser caching headers

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For issues and questions:
- Check the troubleshooting section above
- Review system logs in `/logs` directory
- Create an issue in the project repository
- Contact the development team

---

**🎯 Dashboard URL**: http://localhost:5000  
**🔄 Auto-refresh**: Every 30 seconds  
**📱 Mobile Friendly**: Yes  
**🌐 Browser Support**: Chrome, Firefox, Safari, Edge