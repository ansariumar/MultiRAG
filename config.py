import os

# File upload settings
MAX_CONTENT_LENGTH = 1000 * 1024 * 1024  # 1000MB max file size
UPLOAD_FOLDER_PDF = 'uploads/pdf'
UPLOAD_FOLDER_VIDEO = 'uploads/video'
UPLOAD_FOLDER_TEMP = 'uploads/temp'

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'mp4', 'mov', 'avi', 'mkv'}