from src.user.app import app
from src.user.user_proxy import UserProxy

if __name__ == '__main__':
    # Run seed logic for System Admin at start-up
    user_proxy = UserProxy()
    app.debug = True
    app.config['JSON_AS_ASCII'] = False
    app.run(host='127.0.0.1',
            port=5000,
            threaded=True)