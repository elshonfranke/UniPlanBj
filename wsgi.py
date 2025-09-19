from app import create_app

# Expose a plain Flask app object for the Flask CLI and WSGI servers
app, socketio = create_app()


