"""
Email Report Router
Handles weekly AI performance email report system
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

router = APIRouter()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)


class SendReportRequest(BaseModel):
    user_id: str
    email: str


def build_weekly_report(user_data: dict) -> str:
    """
    Build HTML email content with user's weekly performance report
    """
    sessions = user_data.get("sessions", [])
    streak = user_data.get("streak", {})
    rank = user_data.get("rank", {})
    
    # Calculate stats from last 7 days
    if sessions:
        # Best session this week
        best_session = max(sessions, key=lambda s: s.get("total_score", 0))
        best_score = best_session.get("total_score", 0)
        best_career = best_session.get("career_path", "N/A")
        
        # Average score this week
        avg_score = sum(s.get("total_score", 0) for s in sessions) / len(sessions)
        
        # Career path performance (weakest)
        career_scores = {}
        for s in sessions:
            career = s.get("career_path", "Unknown")
            if career not in career_scores:
                career_scores[career] = []
            career_scores[career].append(s.get("total_score", 0))
        
        weakest_career = "N/A"
        if career_scores:
            weakest_career = min(career_scores.keys(), 
                              key=lambda c: sum(career_scores[c])/len(career_scores[c]))
            weakest_avg = sum(career_scores[weakest_career])/len(career_scores[weakest_career])
    else:
        best_score = 0
        best_career = "N/A"
        avg_score = 0
        weakest_career = "N/A"
    
    # Current streak
    current_streak = streak.get("current_streak", 0)
    
    # Current rank and XP
    rank_title = rank.get("rank_title", "🌱 Fresher")
    xp = rank.get("xp", 0)
    
    # AI tip based on performance
    if avg_score > 40:
        ai_tip = "You're doing great! Try Hard mode next to challenge yourself further."
    elif avg_score > 25:
        ai_tip = "Keep practicing! Focus on your weak areas to improve faster."
    else:
        ai_tip = "Don't give up! Consistency is key 💪 Every session makes you better."
    
    # Build HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #6C3FC8, #1E3A5F); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .stat-box {{ background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .stat-label {{ color: #666; font-size: 14px; }}
            .stat-value {{ color: #1E3A5F; font-size: 24px; font-weight: bold; }}
            .tip-box {{ background: #FFF3CD; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #FFC107; }}
            .button {{ display: inline-block; background: #6C3FC8; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0;">📊 Your Weekly Interview Report</h1>
                <p style="margin: 10px 0 0 0;">Week of {datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            <div class="content">
                <div class="stat-box">
                    <div class="stat-label">🏆 Best Session This Week</div>
                    <div class="stat-value">{best_score}/50 - {best_career}</div>
                </div>
                
                <div class="stat-box">
                    <div class="stat-label">📈 Average Score This Week</div>
                    <div class="stat-value">{avg_score:.1f}/50</div>
                </div>
                
                <div class="stat-box">
                    <div class="stat-label">🔥 Current Streak</div>
                    <div class="stat-value">{current_streak} day{'' if current_streak == 1 else 's'}</div>
                </div>
                
                <div class="stat-box">
                    <div class="stat-label">⚡ Current Rank</div>
                    <div class="stat-value">{rank_title} - {xp} XP</div>
                </div>
                
                <div class="stat-box">
                    <div class="stat-label">🎯 Weakest Area</div>
                    <div class="stat-value">{weakest_career}</div>
                </div>
                
                <div class="tip-box">
                    <strong>💡 AI Tip:</strong><br/>
                    {ai_tip}
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://localhost:3000/interview" class="button">Practice Now</a>
                </div>
            </div>
            <div class="footer">
                <p>Keep up the great work! 🌟</p>
                <p>AI Career Navigator - Your personal interview coach</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


@router.post("/send-report")
async def send_weekly_report(request: SendReportRequest):
    """
    Send weekly performance report email to user
    """
    user_id = request.user_id
    email = request.email
    
    try:
        # Fetch last 7 days sessions
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        sessions_response = supabase.table("interview_sessions").select("*").eq("user_id", user_id).gte("created_at", seven_days_ago).execute()
        sessions = sessions_response.data if sessions_response.data else []
        
        # Fetch streak data
        streak_response = supabase.table("user_streaks").select("*").eq("user_id", user_id).execute()
        streak = streak_response.data[0] if streak_response.data else {}
        
        # Fetch rank data
        rank_response = supabase.table("user_ranks").select("*").eq("user_id", user_id).execute()
        rank = rank_response.data[0] if rank_response.data else {}
        
        # Build user data dict
        user_data = {
            "sessions": sessions,
            "streak": streak,
            "rank": rank
        }
        
        # Build HTML email
        html_content = build_weekly_report(user_data)
        
        # Get email credentials from environment
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        
        if not gmail_user or not gmail_password:
            raise HTTPException(status_code=500, detail="Email not configured. Please set GMAIL_USER and GMAIL_APP_PASSWORD in environment variables.")
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '📊 Your Weekly Interview Report - AI Career Navigator'
        msg['From'] = gmail_user
        msg['To'] = email
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email via Gmail SMTP
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, email, msg.as_string())
        
        return {"success": True, "message": f"Report sent to {email}!"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error sending email report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send report: {str(e)}")


@router.get("/report-preview/{user_id}")
async def get_report_preview(user_id: str):
    """
    Preview weekly report HTML (without sending email)
    """
    try:
        # Fetch last 7 days sessions
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        sessions_response = supabase.table("interview_sessions").select("*").eq("user_id", user_id).gte("created_at", seven_days_ago).execute()
        sessions = sessions_response.data if sessions_response.data else []
        
        # Fetch streak data
        streak_response = supabase.table("user_streaks").select("*").eq("user_id", user_id).execute()
        streak = streak_response.data[0] if streak_response.data else {}
        
        # Fetch rank data
        rank_response = supabase.table("user_ranks").select("*").eq("user_id", user_id).execute()
        rank = rank_response.data[0] if rank_response.data else {}
        
        # Build user data dict
        user_data = {
            "sessions": sessions,
            "streak": streak,
            "rank": rank
        }
        
        # Build and return HTML (don't send)
        html_content = build_weekly_report(user_data)
        
        return {"html": html_content}
        
    except Exception as e:
        print(f"Error generating report preview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")