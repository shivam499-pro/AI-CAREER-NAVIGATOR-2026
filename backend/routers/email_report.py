"""
Email Report Router
Handles weekly AI performance email report system
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from core.supabase_client import supabase
from core.middleware import get_current_user, AuthenticatedUser
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

router = APIRouter()


class SendReportRequest(BaseModel):
    email: str


def build_weekly_report(user_data: dict) -> str:
    sessions = user_data.get("sessions", [])
    streak = user_data.get("streak", {})
    rank = user_data.get("rank", {})

    current_streak = streak.get("current_streak", 0)
    rank_title = rank.get("rank_title", "🌱 Fresher")
    xp = rank.get("xp", 0)

    # Fix 1: Handle zero sessions properly
    if sessions:
        best_session = max(sessions, key=lambda s: s.get("total_score", 0))
        best_score = best_session.get("total_score", 0)
        best_career = best_session.get("career_path", "N/A")
        avg_score = sum(s.get("total_score", 0) for s in sessions) / len(sessions)

        career_scores = {}
        for s in sessions:
            career = s.get("career_path", "Unknown")
            if career not in career_scores:
                career_scores[career] = []
            career_scores[career].append(s.get("total_score", 0))

        # Fix 2: removed unused weakest_avg variable
        weakest_career = min(
            career_scores.keys(),
            key=lambda c: sum(career_scores[c]) / len(career_scores[c])
        ) if career_scores else "N/A"

        if avg_score > 40:
            ai_tip = "You're crushing it! Try Hard mode to push your limits further."
        elif avg_score > 25:
            ai_tip = "Solid progress! Focus on your weakest area to level up faster."
        else:
            ai_tip = "Consistency beats talent. Every session makes you sharper 💪"

        performance_section = f"""
            <div class="stat-box">
                <div class="stat-label">🏆 Best Session This Week</div>
                <div class="stat-value">{best_score}/50 — {best_career}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">📈 Average Score This Week</div>
                <div class="stat-value">{avg_score:.1f}/50</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">🎯 Weakest Area</div>
                <div class="stat-value">{weakest_career}</div>
            </div>
            <div class="tip-box">
                <strong>💡 AI Tip:</strong><br/>
                {ai_tip}
            </div>
        """
    else:
        # Fix 1: Clean no-sessions state instead of broken 0/50 - N/A
        performance_section = """
            <div class="stat-box" style="text-align:center; padding: 30px;">
                <div class="stat-value" style="font-size:18px;">😴 No practice sessions this week</div>
                <p style="color:#666; margin-top:10px;">
                    Even 1 session a week builds interview confidence over time.<br/>
                    Jump back in — your streak is waiting.
                </p>
            </div>
            <div class="tip-box">
                <strong>💡 This Week's Challenge:</strong><br/>
                Complete just one interview session. That's it. Small steps compound.
            </div>
        """

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
                {performance_section}
                <div class="stat-box">
                    <div class="stat-label">🔥 Current Streak</div>
                    <div class="stat-value">{current_streak} day{'' if current_streak == 1 else 's'}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">⚡ Current Rank</div>
                    <div class="stat-value">{rank_title} — {xp} XP</div>
                </div>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://localhost:3000/interview" class="button">Practice Now →</a>
                </div>
            </div>
            <div class="footer">
                <p>Keep going. Every session counts. 🌟</p>
                <p>AI Career Navigator — Your personal interview coach</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


@router.post("/send-report")
async def send_weekly_report(
    request: SendReportRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Send weekly performance report email to user.
    User identity comes from JWT token — not request body.
    """
    email = request.email

    try:
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

        sessions_response = supabase.table("interview_sessions").select("*") \
            .eq("user_id", current_user) \
            .gte("created_at", seven_days_ago).execute()
        sessions = sessions_response.data if sessions_response.data else []

        streak_response = supabase.table("user_streaks").select("*") \
            .eq("user_id", current_user).execute()
        streak = streak_response.data[0] if streak_response.data else {}

        rank_response = supabase.table("user_ranks").select("*") \
            .eq("user_id", current_user).execute()
        rank = rank_response.data[0] if rank_response.data else {}

        user_data = {"sessions": sessions, "streak": streak, "rank": rank}
        html_content = build_weekly_report(user_data)

        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")

        if not gmail_user or not gmail_password:
            raise HTTPException(
                status_code=500,
                detail="Email not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD."
            )

        msg = MIMEMultipart('alternative')
        msg['Subject'] = '📊 Your Weekly Interview Report — AI Career Navigator'
        msg['From'] = gmail_user
        msg['To'] = email
        msg.attach(MIMEText(html_content, 'html'))

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


@router.get("/report-preview")
async def get_report_preview(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Preview weekly report HTML without sending email.
    User identity comes from JWT token.
    """
    try:
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

        sessions_response = supabase.table("interview_sessions").select("*") \
            .eq("user_id", current_user) \
            .gte("created_at", seven_days_ago).execute()
        sessions = sessions_response.data if sessions_response.data else []

        streak_response = supabase.table("user_streaks").select("*") \
            .eq("user_id", current_user).execute()
        streak = streak_response.data[0] if streak_response.data else {}

        rank_response = supabase.table("user_ranks").select("*") \
            .eq("user_id", current_user).execute()
        rank = rank_response.data[0] if rank_response.data else {}

        user_data = {"sessions": sessions, "streak": streak, "rank": rank}
        html_content = build_weekly_report(user_data)

        return {"html": html_content}

    except Exception as e:
        print(f"Error generating report preview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")