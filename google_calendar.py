import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from django.conf import settings
import uuid
from datetime import datetime

class GoogleCalendarService:
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'openid'
        ]
        
    def get_auth_url(self, user_id):
        """Generate OAuth URL for user to authorize Google Calendar access"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=str(user_id)
        )
        
        return auth_url
    
    def exchange_code_for_tokens(self, code, user_id):
        """Exchange authorization code for access tokens"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        return {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_expiry': credentials.expiry
        }
    
    def create_meeting_as_admin(self, start_time, end_time, attendees, summary, booking_id=None):
        """Create Google Calendar event from admin account and send to both parties"""
        try:
            from emn.models import GoogleCalendarToken, EMNUser
            # Get admin user's tokens
            admin_user = EMNUser.objects.filter(email='web@ecell.in').first()
            if not admin_user:
                print("DEBUG: Admin user web@ecell.in not found")
                return self.create_meeting_fallback(start_time, end_time, attendees, summary, booking_id)
            
            admin_token = GoogleCalendarToken.objects.get(user=admin_user)
            credentials = Credentials(
                token=admin_token.access_token,
                refresh_token=admin_token.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET
            )
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Create description with EMN branding
            tracking_url = f'{settings.BASE_URL}/emn/join-meeting/{booking_id}/' if booking_id else 'Meeting link will be provided'
            description = f'''EMN - EUREKA! MENTORSHIP NETWORK

MEETING SCHEDULED: {summary}

JOIN YOUR MEETING: {tracking_url}

ABOUT EMN:
Connecting entrepreneurs with experienced mentors to accelerate business growth and success.

SUPPORT: web@ecell.in

© 2025 Eureka! Mentorship Network'''
            
            event = {
                'summary': f'[EMN] {summary}',
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'attendees': [{
                    'email': email, 
                    'responseStatus': 'needsAction'
                } for email in attendees],
                'guestsCanSeeOtherGuests': False,
                'visibility': 'default',
                'conferenceData': {
                    'createRequest': {
                        'requestId': str(uuid.uuid4()),
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }
            
            print(f"DEBUG: Creating admin event for attendees: {[att['email'] for att in event['attendees']]}")
            
            created_event = service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,
                sendNotifications=True
            ).execute()
            
            print(f"DEBUG: Admin event created successfully with ID: {created_event['id']}")
            
            # Get the actual Google Meet link and extract meet ID
            actual_meet_link = created_event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri', '')
            
            # Extract meet ID from Google Meet URL
            meet_id = ''
            if actual_meet_link and 'meet.google.com/' in actual_meet_link:
                meet_id = actual_meet_link.split('meet.google.com/')[-1].split('?')[0]
            
            # Create tracking URL using meet ID
            tracking_url = f'{settings.BASE_URL}/emn/join-meeting/{meet_id}/' if meet_id else f'{settings.BASE_URL}/emn/join-meeting/{booking_id}/'
            
            return {
                'event_id': created_event['id'],
                'meet_link': tracking_url,
                'actual_meet_link': actual_meet_link,
                'meet_id': meet_id,
                'html_link': created_event.get('htmlLink', '')
            }
            
        except Exception as e:
            print(f"DEBUG: Admin calendar setup error: {e}")
            return self.create_meeting_fallback(start_time, end_time, attendees, summary, booking_id)
    
    def create_meeting_fallback(self, start_time, end_time, attendees, summary, booking_id=None):
        """Fallback method when admin calendar not available"""
        # Generate a placeholder meet link
        import uuid
        meet_id = str(uuid.uuid4())[:8] + '-' + str(uuid.uuid4())[:4] + '-' + str(uuid.uuid4())[:4]
        actual_meet_link = f"https://meet.google.com/{meet_id}"
        tracking_url = f'{settings.BASE_URL}/emn/join-meeting/{meet_id}/'
        
        return {
            'event_id': f'fallback-{booking_id}',
            'meet_link': tracking_url,
            'actual_meet_link': actual_meet_link,
            'meet_id': meet_id,
            'html_link': ''
        }
    
    def create_meeting(self, access_token, refresh_token, start_time, end_time, attendees, summary, booking_id=None):
        """Create Google Calendar event with Meet link"""
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        
        # Create initial description without tracking URL (will update after event creation)
        description = f'''EMN - EUREKA! MENTORSHIP NETWORK

MEETING SCHEDULED: {summary}

JOIN YOUR MEETING: [Meeting link will be updated shortly]

ABOUT EMN:
Connecting entrepreneurs with experienced mentors to accelerate business growth and success.

SUPPORT: web@ecell.in

© 2025 Eureka! Mentorship Network'''
        
        event = {
            'summary': f'[EMN] {summary}',
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
            'attendees': [{
                'email': email, 
                'responseStatus': 'needsAction'
            } for email in attendees],
            'guestsCanSeeOtherGuests': True,
            'visibility': 'public',
            'guestsCanInviteOthers': True,
            'guestsCanModify': False,
            'anyoneCanAddSelf': True,
            'conferenceData': {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),
                    'conferenceSolutionKey': {
                        'type': 'hangoutsMeet'
                    },
                    'status': {
                        'statusCode': 'success'
                    }
                },
                'conferenceId': str(uuid.uuid4()),
                'signature': str(uuid.uuid4())
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 10},
                ],
            },

        }
        
        print(f"DEBUG: Creating event for attendees: {[att['email'] for att in event['attendees']]}")
        
        event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1,
            sendNotifications=False
        ).execute()
        
        print(f"DEBUG: Event created successfully with ID: {event['id']}")
        
        # Get the real Google Meet link from the created event
        actual_meet_link = event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri', '')
        
        # Extract meet ID from real Google Meet URL
        meet_id = ''
        if actual_meet_link and 'meet.google.com/' in actual_meet_link:
            meet_id = actual_meet_link.split('meet.google.com/')[-1].split('?')[0]
        
        # Create tracking URL using real meet ID
        tracking_url = f'{settings.BASE_URL}/emn/join-meeting/{meet_id}/' if meet_id else f'{settings.BASE_URL}/emn/join-meeting/{booking_id}/'
        
        # Update the event description with the correct tracking URL
        if meet_id:
            updated_description = description.replace('[Meeting link will be updated shortly]', tracking_url)
            
            updated_event = {
                'description': updated_description
            }
            
            try:
                service.events().patch(
                    calendarId='primary',
                    eventId=event['id'],
                    body=updated_event
                ).execute()
                print(f"DEBUG: Updated event description with tracking URL: {tracking_url}")
            except Exception as e:
                print(f"DEBUG: Failed to update event description: {e}")
        
        return {
            'event_id': event['id'],
            'meet_link': tracking_url,
            'actual_meet_link': actual_meet_link,
            'meet_id': meet_id,
            'html_link': event.get('htmlLink', '')
        }
    
    def cancel_meeting(self, access_token, refresh_token, event_id):
        """Cancel Google Calendar event"""
        try:
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET
            )
            
            service = build('calendar', 'v3', credentials=credentials)
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            return True
        except Exception as e:
            print(f"DEBUG: Failed to cancel Google Calendar event: {e}")
            return False
    
    def update_meeting(self, access_token, refresh_token, event_id, start_time, end_time, summary=None):
        """Update Google Calendar event time"""
        try:
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET
            )
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Get existing event
            event = service.events().get(calendarId='primary', eventId=event_id).execute()
            
            # Update times
            event['start'] = {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Asia/Kolkata',
            }
            event['end'] = {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Asia/Kolkata',
            }
            
            if summary:
                event['summary'] = f'[EMN] {summary}'
            
            # Update event
            updated_event = service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event,
                sendNotifications=True
            ).execute()
            
            return True
        except Exception as e:
            print(f"DEBUG: Failed to update Google Calendar event: {e}")
            return False