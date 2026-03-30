from supabase import create_client
import os
from dotenv import load_dotenv
import json

load_dotenv()

def check_real_analysis():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    supabase = create_client(url, key)

    user_id = "16ce6dcd-09af-4302-bd89-6cb048386934"
    
    print(f"Fetching analysis for user: {user_id}")
    response = supabase.table("analyses").select("*").eq("user_id", user_id).execute()
    
    if not response.data:
        print("No analysis found in DB.")
        return

    analysis = response.data[0]
    
    print("\n--- REAL AI ANALYSIS SUMMARY ---")
    print(f"Experience Level: {analysis.get('experience_level')}")
    print(f"Strengths: {', '.join(analysis.get('strengths', []))}")
    
    career_paths = analysis.get("career_paths", [])
    if career_paths:
        print("\nTop Career Path Recommended:")
        print(f"- {career_paths[0].get('name')} ({career_paths[0].get('match_percentage')}% Match)")
        print(f"  Reason: {career_paths[0].get('reason')}")

    roadmap = analysis.get("roadmap", {})
    if roadmap:
        print(f"\nRoadmap Title: {roadmap.get('target_career')}")
        print(f"Total Weeks: {roadmap.get('total_weeks')}")
        milestones = roadmap.get("milestones", [])
        if milestones:
            print(f"Sample Week 1 Milestone: {milestones[0].get('title')}")

if __name__ == "__main__":
    check_real_analysis()
