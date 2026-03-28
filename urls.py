from django.urls import path
from .views import auth_views, content_views, dashboard_views, connection_views, startup_views, booking_views, meeting_views

urlpatterns = [
    # Auth URLs
    path('email-verification/', auth_views.EmailVerificationView.as_view(), name='email_verification'),
    path('otp-verification/', auth_views.OTPVerificationView.as_view(), name='otp_verification'),
    path('mentor-registration/', auth_views.MentorRegView.as_view(), name='mentor_registration'),
    path('mentor-login/', auth_views.MentorLoginView.as_view(), name='mentor_login'),
    path('startup-login/', startup_views.StartupLoginView.as_view(), name='startup_login'),
    path('mentor-profile/', auth_views.MentorProfileView.as_view(), name='mentor_profile'),
    path('profile/', auth_views.ProfileView.as_view(), name='profile'),
    path('forgot-password/', auth_views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', auth_views.ResetPasswordView.as_view(), name='reset_password'),
    path('check-email/', auth_views.CheckEmailView.as_view(), name='check_email'),
    path('set-password/', auth_views.SetPasswordView.as_view(), name='set_password'),
    
    # Content URLs
    path('faqs/', content_views.FAQView.as_view(), name='faqs'),
    path('testimonials/', content_views.TestimonialView.as_view(), name='testimonials'),
    path('connected-mentors/', content_views.ConnectedMentorView.as_view(), name='connected_mentors'),
    path('past-winners/', content_views.PastWinnerView.as_view(), name='past_winners'),
    path('contact-profiles/', content_views.ContactProfileView.as_view(), name='contact_profiles'),
    path('get-mentor-email/', content_views.GetAMentorEmailView.as_view(), name='get_mentor_email'),
    path('site-settings/', content_views.SiteSettingsView.as_view(), name='site_settings'),
    
    # Dashboard URLs
    path('mentor-dashboard/', dashboard_views.mentor_dashboard, name='mentor_dashboard'),
    path('startup-dashboard/', dashboard_views.startup_dashboard, name='startup_dashboard'),
    path('send-connection-request/', dashboard_views.send_connection_request, name='send_connection_request'),
    path('respond-connection-request/<int:request_id>/', dashboard_views.respond_connection_request, name='respond_connection_request'),
    path('connections/', dashboard_views.get_connections, name='get_connections'),
    path('send-email/<int:user_id>/', dashboard_views.send_email_to_connection, name='send_email_to_connection'),
    
    # Email connection URLs (secure token-based)
    path('connection/accept/<str:token>/', dashboard_views.respond_connection_request_by_token, name='accept_connection_token'),
    path('connection/reject/<str:token>/', dashboard_views.respond_connection_request_by_token, name='reject_connection_token'),
    # Legacy connection URLs
    path('connection/accept/<int:request_id>/', connection_views.accept_connection, name='accept_connection'),
    path('connection/reject/<int:request_id>/', connection_views.reject_connection, name='reject_connection'),
    
    # Booking URLs
    path('weekly-availability/', booking_views.weekly_availability, name='weekly_availability'),
    path('create-availability-slot/', booking_views.create_availability_slot, name='create_availability_slot'),
    path('get-availability-slots/', booking_views.get_availability_slots, name='get_availability_slots'),
    path('book-slot/', booking_views.book_slot, name='book_slot'),
    path('my-bookings/', booking_views.my_bookings, name='my_bookings'),
    path('startups/', booking_views.get_startups, name='get_startups'),
    
    # Google Calendar OAuth
    path('google-calendar-auth/', booking_views.google_calendar_auth, name='google_calendar_auth'),
    path('google-calendar-status/', booking_views.google_calendar_status, name='google_calendar_status'),
    path('google-callback/', booking_views.google_callback, name='google_callback'),
    
    # Meeting tracking
    path('join-meeting/<str:meet_identifier>/', booking_views.join_meeting, name='join_meeting'),
    path('google-calendar-disconnect/', booking_views.google_calendar_disconnect, name='google_calendar_disconnect'),
    
    # Meeting management endpoints
    path('meetings/', meeting_views.list_meetings, name='list_meetings'),
    path('meetings/all/', meeting_views.list_all_meetings, name='list_all_meetings'),
    path('meetings/book/', meeting_views.book_meeting, name='book_meeting'),
    path('meetings/booked-slots/<int:startup_id>/', meeting_views.get_booked_slots, name='get_booked_slots'),
    path('meetings/request-reschedule/', meeting_views.request_reschedule, name='request_reschedule'),
    path('meetings/reschedule/', meeting_views.reschedule_meeting, name='reschedule_meeting'),
    path('meetings/<int:meeting_id>/cancel/', meeting_views.cancel_meeting, name='cancel_meeting'),
    path('debug/user-info/', meeting_views.debug_user_info, name='debug_user_info'),
]