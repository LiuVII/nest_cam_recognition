import os
import json

# OAuth2 client ID and secret copied from https://console.developers.nest.com/products/(selected product)
# Keep product ID and product secret private (don't store this in a public location).
with open('credentials.json', 'r') as credfile:
    json_str = credfile.read()
    json_data = json.loads(json_str)

    product_id = json_data["PRODUCT_ID"]
    product_secret = json_data["PRODUCT_SECRET"]
    authorization_code = json_data["authorization_code"]
    video_url = json_data["VIDEO_URL"]

# Port number for sample application and callback URI (must be the same port)
port = 5000  

snapshot_dir = "./snapshots"
known_faces_dir = "./known_faces"
results_dir = "./results"
interactions_dir = "./interactions"
unknown = "unknown"

# OAuth2 URLs
nest_auth_url = 'https://home.nest.com/login/oauth2'
nest_access_token_url = 'https://api.home.nest.com/oauth2/access_token'
nest_api_root_url = 'https://api.home.nest.com'
nest_tokens_path = '/oauth2/access_tokens/'

# API URL after authorization
nest_api_url = "https://developer-api.nest.com"

# URL to exclude (if camera has this snapshot URL then getting 404 not found errors tyring to download)
sim_snapshot_url = 'https://developer.nest.com/simulator/api/v1/nest/devices/camera/snapshot'