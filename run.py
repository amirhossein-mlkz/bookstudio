"""Safe Windows launcher. Run with: python run.py"""
import socket

def port_in_use(host='127.0.0.1', port=5000):
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False

if __name__ == '__main__':
    if port_in_use():
        raise SystemExit('Port 5000 is already in use. Close the older Book Studio process before launching this version.')
    from bookstudio.app import main
    main()
