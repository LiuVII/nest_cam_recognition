from flask import Flask, request, jsonify, abort

app = Flask(__name__)

@app.route("/msg", methods=["POST"])
def print_msg():
    response = jsonify({'status': 'OK'})
    print("msg received: {0}".format(request.values.get('aody')))
    response.status_code = 201
    return response

if __name__ == "__main__":
    app.run()