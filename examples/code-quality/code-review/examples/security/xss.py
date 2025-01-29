from flask import Flask, request

app = Flask(__name__)


@app.route("/profile")
def user_profile():
    """
    Displays user profile information.
    WARNING: This endpoint is vulnerable to XSS!
    """
    # Vulnerable: Unescaped user input directly in HTML
    username = request.args.get("username", "")
    return f"""
        <html>
            <body>
                <h1>Welcome, {username}!</h1>
                <div>Your profile information:</div>
            </body>
        </html>
    """


if __name__ == "__main__":
    app.run(debug=True)
