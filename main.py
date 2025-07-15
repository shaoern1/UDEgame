import streamlit as st
import json
import random
import openai
from openai import OpenAI
import os
import dotenv
import re

dotenv.load_dotenv()
# Load OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Sample scenarios data
scenarios = [
    {
        "title": "The New Team Member",
        "scenario": "A shy new colleague sits alone at lunch every day. How do you help them feel welcome without being pushy?"
    },
    {
        "title": "The Blame Game",
        "scenario": "A project failed and team members are pointing fingers at each other. As a team member, how do you help move forward constructively?"
    },
    {
        "title": "The Difficult Client",
        "scenario": "A client is consistently rude and dismissive during meetings. How do you maintain professionalism while addressing the situation?"
    },
    {
        "title": "The Overworked Colleague",
        "scenario": "You notice a teammate is staying very late every day and seems stressed. How do you offer support without overstepping boundaries?"
    },
    {
        "title": "The Communication Breakdown",
        "scenario": "Two departments are not sharing important information, causing project delays. How do you facilitate better communication?"
    },
    {
        "title": "The Late Arrival",
        "scenario": "You are late for work and your boss is angry. What would you do?"
    },
    {
        "title": "The Credit Stealer",
        "scenario": "A coworker takes credit for your idea in a team meeting. How do you handle this professionally?"
    },
    {
        "title": "The Tech Meltdown",
        "scenario": "Your computer crashes the morning of a big presentation, taking your work with it. The presentation is in 2 hours. What do you do?"
    }
]

# System prompt for GPT
SYSTEM_PROMPT = """You are an engaging workplace skills instructor who uses interactive scenarios with constructive feedback and light humor to teach professional behavior.

## Task Format

### Ranking System
🥇 GOLD MEDAL: Best response (⭐⭐⭐⭐⭐)  
🥈 SILVER MEDAL: Good with minor issues (⭐⭐⭐⭐)  
🥉 BRONZE MEDAL: Okay but needs improvement (⭐⭐⭐)  
🤔 PARTICIPATION TROPHY: Poor but shows effort (⭐⭐)  
🚨 "We Need to Talk": Major issues (⭐)

### Feedback Requirements
For each answer include:
- Clear reasoning for ranking
- Specific strengths/weaknesses
- Light, appropriate humor (workplace metaphors, gentle sarcasm, pop culture references)
- Constructive suggestions
- Professional context (why this matters at work)

### Learning Lesson Structure
End with:
- Key principle/framework (bolded)
- Practical application
- Why it matters professionally
- Bonus tip: Memorable, actionable advice

## Evaluation Criteria
Rate based on: Professionalism • Problem-solving • Accountability • Communication • Workplace awareness • Practical applicability

## Guidelines
- Keep humor light and encouraging (never mocking)
- Be constructive and end positively
- Make lessons actionable and memorable
- Use emojis sparingly but effectively

Please evaluate the responses and provide rankings with feedback. IMPORTANT: For each player's response, clearly indicate which medal/trophy they receive (🥇 GOLD MEDAL, 🥈 SILVER MEDAL, etc.) so scores can be calculated."""

def get_llm_analysis(scenario_text, answers, player_names, api_key, model="gpt-3.5-turbo"):
    """Get analysis from OpenAI API"""
    try:
        client = OpenAI(api_key=api_key)
        
        # Format the answers for the prompt
        formatted_answers = ""
        for i, (name, answer) in enumerate(zip(player_names, answers), 1):
            formatted_answers += f"{name}: {answer}\n\n"
        
        user_prompt = f"""
Scenario: {scenario_text}

Student Answers:
{formatted_answers}

Please evaluate these responses using the ranking system and provide feedback with a learning lesson. Make sure to clearly identify which medal/trophy each player receives.
"""
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=4096,
            temperature=0.7
        )
        
        return response.choices[0].message.content, None
    except Exception as e:
        return None, str(e)

def extract_scores_from_analysis(analysis_text, player_names):
    """Extract scores from AI analysis based on medals/trophies awarded"""
    scores = {}
    
    # Score mapping
    score_map = {
        "🥇": 10,  # Gold Medal
        "🥈": 10,  # Silver Medal  
        "🥉": 10,  # Bronze Medal
        "🤔": 10,  # Participation Trophy
        "🚨": 10   # "We Need to Talk"
    }
    
    # Try to find medals for each player
    for name in player_names:
        scores[name] = 0  # Default score
        
        # Look for medal mentions with player name nearby
        for medal, points in score_map.items():
            if medal in analysis_text:
                # Simple heuristic: if medal appears, check if player name is nearby
                medal_index = analysis_text.find(medal)
                if medal_index != -1:
                    # Look for player name within 200 characters of the medal
                    context = analysis_text[max(0, medal_index-100):medal_index+100]
                    if name.lower() in context.lower():
                        scores[name] = points
                        break
    
    return scores

def initialize_session_state():
    """Initialize all session state variables"""
    if 'current_scenario' not in st.session_state:
        st.session_state.current_scenario = None
    if 'current_player' not in st.session_state:
        st.session_state.current_player = 1
    if 'num_players' not in st.session_state:
        st.session_state.num_players = 3
    if 'player_names' not in st.session_state:
        st.session_state.player_names = []
    if 'submitted_answers' not in st.session_state:
        st.session_state.submitted_answers = []
    if 'all_submitted' not in st.session_state:
        st.session_state.all_submitted = False
    if 'llm_analysis' not in st.session_state:
        st.session_state.llm_analysis = None
    if 'show_analysis' not in st.session_state:
        st.session_state.show_analysis = False
    if 'player_scores' not in st.session_state:
        st.session_state.player_scores = {}
    if 'round_number' not in st.session_state:
        st.session_state.round_number = 1
    if 'game_ended' not in st.session_state:
        st.session_state.game_ended = False
    if 'winner' not in st.session_state:
        st.session_state.winner = None

def check_for_winner():
    """Check if any player has reached 10 points and end the game"""
    if st.session_state.player_scores:
        max_score = max(st.session_state.player_scores.values())
        if max_score >= 10:
            # Find the winner (player with highest score)
            winner = max(st.session_state.player_scores.items(), key=lambda x: x[1])
            st.session_state.winner = winner[0]
            st.session_state.game_ended = True
            return True
    return False

def reset_round():
    """Reset for a new round but keep scores"""
    st.session_state.current_scenario = None
    st.session_state.current_player = 1
    st.session_state.submitted_answers = []
    st.session_state.all_submitted = False
    st.session_state.llm_analysis = None
    st.session_state.show_analysis = False
    
    # Ensure current_player doesn't exceed number of players
    if hasattr(st.session_state, 'player_names') and st.session_state.player_names:
        if st.session_state.current_player > len(st.session_state.player_names):
            st.session_state.current_player = 1

def reset_game():
    """Reset entire game including scores"""
    st.session_state.current_scenario = None
    st.session_state.current_player = 1
    st.session_state.submitted_answers = []
    st.session_state.all_submitted = False
    st.session_state.llm_analysis = None
    st.session_state.show_analysis = False
    st.session_state.player_scores = {}
    st.session_state.round_number = 1
    st.session_state.player_names = []
    st.session_state.game_ended = False
    st.session_state.winner = None

def main():
    st.set_page_config(page_title="Office Scenario Training Game", page_icon="🏢", layout="wide")
    
    st.title("🏢 Office Scenario Training Game")
    st.markdown("*Learn workplace skills through interactive scenarios with AI feedback*")
    
    # Initialize session state
    initialize_session_state()
    
    # Sidebar for controls
    with st.sidebar:
        st.header("🔧 Game Controls")
        
        # Game setup
        st.subheader("🎮 Game Setup")
        
        # Number of players (only allow change when no game in progress)
        if not st.session_state.current_scenario:
            new_num_players = st.slider("Number of players:", 2, 6, st.session_state.num_players)
            if new_num_players != st.session_state.num_players:
                st.session_state.num_players = new_num_players
                st.session_state.player_names = []
                st.session_state.player_scores = {}
        else:
            st.write(f"**Players in game:** {st.session_state.num_players}")
        
        # Player name setup
        if not st.session_state.player_names or len(st.session_state.player_names) != st.session_state.num_players:
            st.write("**Enter player names:**")
            names = []
            for i in range(st.session_state.num_players):
                name = st.text_input(f"Player {i+1} name:", key=f"name_{i}", value=f"Player {i+1}")
                names.append(name)
            
            if st.button("✅ Confirm Players"):
                st.session_state.player_names = names
                # Initialize scores for new players
                for name in names:
                    if name not in st.session_state.player_scores:
                        st.session_state.player_scores[name] = 0
                st.rerun()
        
        # Show current scores
        if st.session_state.player_names and st.session_state.player_scores:
            st.subheader("🏆 Current Scores")
            sorted_scores = sorted(st.session_state.player_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Check if anyone is close to winning
            max_score = sorted_scores[0][1] if sorted_scores else 0
            if max_score >= 8 and not st.session_state.game_ended:
                st.warning(f"⚡ {sorted_scores[0][0]} is close to winning! (Need 10 points)")
            
            for i, (name, score) in enumerate(sorted_scores):
                if i == 0:
                    if score >= 10:
                        st.write(f"🏆 **{name}**: {score} points (WINNER!)")
                    else:
                        st.write(f"👑 **{name}**: {score} points")
                else:
                    st.write(f"🎯 **{name}**: {score} points")
            
            st.write(f"**Round:** {st.session_state.round_number}")
            st.caption("🎯 First to 10 points wins!")
        
        st.divider()
        
        # OpenAI API Configuration
        st.subheader("🤖 AI Configuration")
        
        # Use environment variable as default, but allow override
        default_key = OPENAI_API_KEY if OPENAI_API_KEY else ""
        api_key = st.text_input(
            "OpenAI API Key",
            value=default_key,
            type="password",
            help="Enter your OpenAI API key to enable AI analysis"
        )
        
        model_choice = st.selectbox(
            "Model",
            ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
            help="Select the OpenAI model for analysis"
        )
        
        # Show API status
        if api_key:
            st.success("✅ API Key provided")
        else:
            st.warning("⚠️ No API Key - AI analysis disabled")
        
        st.divider()
        
        # Game controls
        if st.button("🎲 Start New Round", type="primary", disabled=st.session_state.game_ended):
            reset_round()
            st.session_state.current_scenario = random.choice(scenarios)
            st.rerun()
        
        if st.button("🔄 Reset Game"):
            reset_game()
            st.rerun()
        
        # Show game status
        if st.session_state.game_ended:
            st.error(f"🏆 GAME OVER! {st.session_state.winner} WINS!")
            st.write("Click 'Reset Game' to start a new game")
        
        # Scenario selection dropdown
        if not st.session_state.current_scenario and not st.session_state.game_ended:
            st.subheader("📋 Choose Scenario")
            scenario_titles = ["Select a scenario..."] + [s["title"] for s in scenarios]
            selected_title = st.selectbox("Available scenarios:", scenario_titles)
            
            if selected_title != "Select a scenario...":
                selected_scenario = next(s for s in scenarios if s["title"] == selected_title)
                if st.button(f"Use: {selected_title}"):
                    reset_round()
                    st.session_state.current_scenario = selected_scenario
                    st.rerun()
    
    # Main content area
    if not st.session_state.player_names:
        st.info("👈 Please set up player names in the sidebar to start!")
        return
    
    # Check if game has ended - show victory screen
    if st.session_state.game_ended:
        st.balloons()  # Celebration animation
        
        st.header("🏆 GAME OVER! 🏆")
        st.subheader(f"🎉 Congratulations {st.session_state.winner}! 🎉")
        st.write(f"**{st.session_state.winner}** has reached 10 points and won the game!")
        
        # Show final standings
        st.subheader("🏅 Final Standings")
        sorted_scores = sorted(st.session_state.player_scores.items(), key=lambda x: x[1], reverse=True)
        
        cols = st.columns(len(sorted_scores))
        for i, (name, total_score) in enumerate(sorted_scores):
            with cols[i]:
                if i == 0:
                    st.metric(f"🥇 {name}", f"{total_score} pts", delta="WINNER! 🏆")
                elif i == 1:
                    st.metric(f"🥈 {name}", f"{total_score} pts", delta="2nd Place")
                elif i == 2:
                    st.metric(f"🥉 {name}", f"{total_score} pts", delta="3rd Place")
                else:
                    st.metric(f"#{i+1} {name}", f"{total_score} pts")
        
        # Game stats
        st.subheader("📊 Game Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rounds", st.session_state.round_number - 1)
        with col2:
            st.metric("Winning Score", st.session_state.player_scores[st.session_state.winner])
        with col3:
            avg_score = sum(st.session_state.player_scores.values()) / len(st.session_state.player_scores)
            st.metric("Average Score", f"{avg_score:.1f}")
        
        # New game option
        st.info("👈 Click 'Reset Game' in the sidebar to start a new game!")
        return
    
    if st.session_state.current_scenario is None:
        st.info("👈 Click 'Start New Round' or choose a scenario from the sidebar!")
        
        # Show preview of available scenarios
        st.subheader("📚 Available Scenarios Preview:")
        for i, scenario in enumerate(scenarios, 1):
            with st.expander(f"{i}. {scenario['title']}"):
                st.write(scenario['scenario'])
        return
    
    # Display current scenario
    scenario = st.session_state.current_scenario
    
    st.subheader(f"📋 Round {st.session_state.round_number}: {scenario['title']}")
    st.info(scenario['scenario'])
    
    # Show progress
    total_players = len(st.session_state.player_names)
    submitted_count = len(st.session_state.submitted_answers)
    
    # Safety check: if somehow we have more submissions than players, trim the list
    if submitted_count > total_players:
        st.session_state.submitted_answers = st.session_state.submitted_answers[:total_players]
        submitted_count = len(st.session_state.submitted_answers)
    
    # Ensure progress is between 0 and 1
    progress = min(submitted_count / total_players, 1.0) if total_players > 0 else 0.0
    st.progress(progress, text=f"Progress: {submitted_count}/{total_players} players submitted")
    
    # Auto-complete if we somehow have all responses but flag not set
    if submitted_count >= total_players and not st.session_state.all_submitted:
        st.session_state.all_submitted = True
    
    # Sequential player input
    if not st.session_state.all_submitted:
        current_player_idx = st.session_state.current_player - 1
        
        # Safety check: ensure we don't go out of bounds
        if current_player_idx >= len(st.session_state.player_names):
            st.session_state.all_submitted = True
            st.rerun()
            return
            
        current_player_name = st.session_state.player_names[current_player_idx]
        
        st.subheader(f"🎯 {current_player_name}'s Turn")
        st.write(f"**Player {st.session_state.current_player} of {total_players}**")
        
        # Show who has already submitted
        if st.session_state.submitted_answers:
            st.write("**Already submitted:**")
            for i, name in enumerate(st.session_state.player_names[:len(st.session_state.submitted_answers)]):
                st.write(f"✅ {name}")
        
        # Current player input
        player_response = st.text_area(
            f"How would you handle this situation, {current_player_name}?",
            height=150,
            placeholder="Enter your response here...",
            key=f"current_response_{st.session_state.round_number}_{st.session_state.current_player}"
        )
        
        if st.button(f"Submit Response for {current_player_name}", type="primary"):
            if player_response.strip():
                # Safety check: don't add more responses than players
                if len(st.session_state.submitted_answers) < total_players:
                    st.session_state.submitted_answers.append(player_response.strip())
                
                if st.session_state.current_player < total_players:
                    st.session_state.current_player += 1
                    st.success(f"✅ {current_player_name}'s response submitted!")
                    st.rerun()
                else:
                    st.session_state.all_submitted = True
                    st.success("🎉 All players have submitted their responses!")
                    st.rerun()
            else:
                st.error("⚠️ Please enter a response before submitting!")
    
    # All players submitted - show analysis option
    elif st.session_state.all_submitted and not st.session_state.show_analysis:
        st.subheader("🎉 All Responses Submitted!")
        
        # Show all submitted responses
        st.subheader("📋 All Responses")
        for i, (name, answer) in enumerate(zip(st.session_state.player_names, st.session_state.submitted_answers)):
            with st.expander(f"{name}'s Response"):
                st.write(answer)
        
        # Get AI analysis
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🤖 Get AI Analysis & Scores", type="primary", disabled=not api_key):
                with st.spinner("🧠 AI instructor is analyzing responses and calculating scores..."):
                    analysis, error = get_llm_analysis(
                        scenario['scenario'], 
                        st.session_state.submitted_answers, 
                        st.session_state.player_names,
                        api_key, 
                        model_choice
                    )
                    
                    if analysis:
                        st.session_state.llm_analysis = analysis
                        st.session_state.show_analysis = True
                        
                        # Extract and update scores
                        round_scores = extract_scores_from_analysis(analysis, st.session_state.player_names)
                        for name, score in round_scores.items():
                            st.session_state.player_scores[name] = st.session_state.player_scores.get(name, 0) + score
                        
                        # Check for winner after updating scores
                        game_ended = check_for_winner()
                        
                        if game_ended:
                            st.success(f"✅ Analysis complete! 🏆 GAME OVER - {st.session_state.winner} WINS!")
                        else:
                            st.success("✅ Analysis complete and scores updated!")
                        st.rerun()
                    else:
                        st.error(f"❌ Analysis failed: {error}")
        
        with col2:
            if st.button("⏭️ Skip to Next Round", disabled=st.session_state.game_ended):
                st.session_state.round_number += 1
                reset_round()
                st.rerun()
    
    # Display AI analysis and results
    elif st.session_state.show_analysis and st.session_state.llm_analysis:
        st.subheader("🎯 AI Instructor Analysis")
        st.markdown(st.session_state.llm_analysis)
        
        # Show updated scores
        st.subheader("🏆 Updated Scores")
        sorted_scores = sorted(st.session_state.player_scores.items(), key=lambda x: x[1], reverse=True)
        
        cols = st.columns(len(sorted_scores))
        for i, (name, total_score) in enumerate(sorted_scores):
            with cols[i]:
                if i == 0:
                    st.metric(f"👑 {name}", f"{total_score} pts", delta="Leader!")
                else:
                    leader_score = sorted_scores[0][1]
                    diff = total_score - leader_score
                    st.metric(f"🎯 {name}", f"{total_score} pts", delta=f"{diff:+d}")
        
        # Next round button
        if not st.session_state.game_ended:
            if st.button("🎲 Start Next Round", type="primary"):
                st.session_state.round_number += 1
                reset_round()
                st.session_state.current_scenario = random.choice(scenarios)
                st.rerun()
        else:
            st.info(f"🏆 Game Over! {st.session_state.winner} has won with {st.session_state.player_scores[st.session_state.winner]} points!")
            st.write("👈 Click 'Reset Game' in the sidebar to start a new game.")
        
        # Download options
        st.subheader("💾 Download Options")
        
        # Create comprehensive report
        report = f"""# Office Scenario Training Report - Round {st.session_state.round_number}
        
## Scenario: {scenario['title']}
{scenario['scenario']}

## Player Responses:
"""
        for name, answer in zip(st.session_state.player_names, st.session_state.submitted_answers):
            report += f"\n**{name}:** {answer}\n"
        
        report += f"\n## AI Analysis:\n{st.session_state.llm_analysis}"
        
        report += f"\n## Current Scores:\n"
        for name, score in sorted_scores:
            report += f"- {name}: {score} points\n"
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📄 Download Round Report",
                data=report,
                file_name=f"round_{st.session_state.round_number}_report.md",
                mime="text/markdown"
            )
        
        with col2:
            # JSON format
            json_output = {
                "round": st.session_state.round_number,
                "scenario": scenario,
                "responses": dict(zip(st.session_state.player_names, st.session_state.submitted_answers)),
                "ai_analysis": st.session_state.llm_analysis,
                "scores": st.session_state.player_scores,
                "model_used": model_choice
            }
            
            st.download_button(
                label="📊 Download JSON",
                data=json.dumps(json_output, indent=2),
                file_name=f"round_{st.session_state.round_number}_data.json",
                mime="application/json"
            )

if __name__ == "__main__":
    main()