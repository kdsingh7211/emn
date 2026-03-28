from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse
from ..models import ConnectionRequest, Connection, EMNUser

@api_view(['GET'])
def accept_connection(request, request_id):
    """Accept connection request via email link"""
    conn_request = get_object_or_404(ConnectionRequest, id=request_id)
    
    if conn_request.status == 'pending':
        conn_request.status = 'accepted'
        conn_request.save()
        
        # Create connection
        Connection.objects.create(
            user1=conn_request.sender,
            user2=conn_request.receiver
        )
        
        return HttpResponse("Connection accepted! You can close this window.")
    
    return HttpResponse("This request has already been processed.")

@api_view(['GET'])
def reject_connection(request, request_id):
    """Reject connection request via email link"""
    conn_request = get_object_or_404(ConnectionRequest, id=request_id)
    
    if conn_request.status == 'pending':
        conn_request.status = 'declined'
        conn_request.save()
        
        return HttpResponse("Connection declined! You can close this window.")
    
    return HttpResponse("This request has already been processed.")