from pymongo import MongoClient
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, mongo_uri):
        try:
            self.client = MongoClient(mongo_uri)
            self.db = self.client["ctf-2025-bot"]
            self.participants = self.db["participants"]
            self.teams = self.db["teams"]
            self.cv = self.db["cv"]
            self.event_state = self.db["event_state"]
            if self.event_state.count_documents({"event_id": "CTF2025"}) == 0:
                self.event_state.insert_one({"event_id": "CTF2025", "current_state": "registration"})
            logger.info("Connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def is_user_registered(self, user_id):
        try:
            return self.participants.find_one({"user_id": user_id}) is not None
        except Exception as e:
            logger.error(f"Error checking user registration for {user_id}: {e}")
            return False

    def is_user_in_team(self, user_id):
        try:
            participant = self.participants.find_one({"user_id": user_id})
            return participant is not None and participant.get("team_id") is not None
        except Exception as e:
            logger.error(f"Error checking team status for user {user_id}: {e}")
            return False

    def add_team(self, team_name, user_id, password=None):
        try:
            team = self.teams.find_one({"team_name": team_name})
            if team:
                if len(team["members"]) >= 4:
                    return None, False
                if team.get("password") and team["password"] != password:
                    return None, False
                team_id = team["_id"]
                self.teams.update_one({"_id": team_id}, {"$push": {"members": user_id}})
                logger.info(f"User {user_id} added to existing team {team_name}")
                return team_id, True
            else:
                team_data = {
                    "team_name": team_name,
                    "category": "CTF2025",
                    "members": [user_id],
                    "is_participant": False,
                    "test_task_status": False
                }
                if password:
                    team_data["password"] = password
                team_result = self.teams.insert_one(team_data)
                logger.info(f"Created new team {team_name} for user {user_id}")
                return team_result.inserted_id, True
        except Exception as e:
            logger.error(f"Error adding team for {user_id}: {e}")
            return None, False

    def add_participant(self, user_id, name, age, university, specialty, course, source, phone, data_consent, team_id, chat_id):
        try:
            self.participants.insert_one({
                "user_id": user_id,
                "name": name,
                "age": age,
                "university": university,
                "specialty": specialty,
                "course": course,
                "source": source,
                "data_consent": data_consent,
                "phone": phone,
                "team_id": team_id,
                "chat_id": chat_id,
                "registration_date": datetime.now().isoformat()
            })
            logger.info(f"Added participant {user_id} to DB")
        except Exception as e:
            logger.error(f"Failed to add participant {user_id}: {e}")
            raise

    def leave_team(self, user_id):
        try:
            participant = self.participants.find_one({"user_id": user_id})
            if participant and participant.get("team_id"):
                team_id = participant["team_id"]
                self.teams.update_one({"_id": team_id}, {"$pull": {"members": user_id}})
                self.participants.update_one({"user_id": user_id}, {"$set": {"team_id": None}})
                logger.info(f"User {user_id} left team {team_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error leaving team for user {user_id}: {e}")
            return False

    def get_user_data(self, user_id):
        try:
            participant = self.participants.find_one({"user_id": user_id})
            return participant["name"] if participant else "друже"
        except Exception as e:
            logger.error(f"Error getting user data for {user_id}: {e}")
            return "друже"

    def get_teams(self):
        try:
            return list(self.teams.find())
        except Exception as e:
            logger.error(f"Error getting teams: {e}")
            return []

    def get_participants(self):
        try:
            return list(self.participants.find())
        except Exception as e:
            logger.error(f"Error getting participants: {e}")
            return []

    def delete_participant(self, user_id):
        try:
            participant = self.participants.find_one({"user_id": user_id})
            if participant:
                self.teams.update_one({"_id": participant["team_id"]}, {"$pull": {"members": user_id}})
                self.participants.delete_one({"user_id": user_id})
                logger.info(f"Deleted participant {user_id} from DB")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting participant {user_id}: {e}")
            return False

    def save_cv(self, user_id, file_id, file_name):
        try:
            self.cv.update_one(
                {"user_id": user_id},
                {"$set": {"file_id": file_id, "file_name": file_name, "upload_date": datetime.now().isoformat()}},
                upsert=True
            )
            logger.info(f"Saved CV for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving CV for user {user_id}: {e}")
            raise

    def get_cv(self, user_id):
        try:
            cv = self.cv.find_one({"user_id": user_id})
            return cv if cv else None
        except Exception as e:
            logger.error(f"Error retrieving CV for user {user_id}: {e}")
            return None

    def delete_admin_collection(self):
        try:
            self.db["admin"].drop()
            logger.info("Dropped admin collection")
        except Exception as e:
            logger.error(f"Error dropping admin collection: {e}")
            raise

    def set_team_participant_status(self, team_id, status):
        try:
            self.teams.update_one({"_id": team_id}, {"$set": {"is_participant": status}})
            logger.info(f"Updated is_participant to {status} for team {team_id}")
        except Exception as e:
            logger.error(f"Error updating is_participant for team {team_id}: {e}")
            raise

    def set_team_test_task_status(self, team_id, status):
        try:
            self.teams.update_one({"_id": team_id}, {"$set": {"test_task_status": status}})
            if status:
                self.set_team_participant_status(team_id, True) 
            logger.info(f"Updated test_task_status to {status} for team {team_id}")
        except Exception as e:
            logger.error(f"Error updating test_task_status for team {team_id}: {e}")
            raise

    def get_team_status(self, team_id):
        try:
            team = self.teams.find_one({"_id": team_id})
            if team:
                return {"is_participant": team.get("is_participant", False), "test_task_status": team.get("test_task_status", False)}
            return {"is_participant": False, "test_task_status": False}
        except Exception as e:
            logger.error(f"Error getting team status for {team_id}: {e}")
            return {"is_participant": False, "test_task_status": False}

    def set_event_state(self, state):
        try:
            valid_states = ["registration", "test_task", "main_task", "finished"]
            if state not in valid_states:
                raise ValueError(f"Invalid state: {state}. Must be one of {valid_states}")
            self.event_state.update_one({"event_id": "CTF2025"}, {"$set": {"current_state": state}}, upsert=True)
            logger.info(f"Set event state to {state}")
        except Exception as e:
            logger.error(f"Error setting event state to {state}: {e}")
            raise

    def get_event_state(self):
        try:
            event = self.event_state.find_one({"event_id": "CTF2025"})
            return event["current_state"] if event else "registration"
        except Exception as e:
            logger.error(f"Error getting event state: {e}")
            return "registration"