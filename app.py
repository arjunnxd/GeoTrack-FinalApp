from flask import Flask, request, jsonify, send_from_directory, render_template
from pymongo import MongoClient
import bcrypt
from bson.objectid import ObjectId
from twilio.rest import Client
import random
import os
from datetime import datetime
from math import radians, cos, sin, sqrt, atan2

# --- Initialize Flask App (ONLY ONCE) ---
app = Flask(__name__)

# --- Page Rendering Routes ---

@app.route('/')
def get_started():
    return render_template('getstarted.html')

@app.route('/signin')
def signin():
    return render_template('signin.html')

@app.route('/create-account')
def create_account():
    return render_template('createaccount.html')

@app.route('/account-settings')
def account_settings():
    return render_template('accountsettings.html')

@app.route('/personal-info')
def personal_info():
    return render_template('personalinfo.html')

@app.route('/vehicle-info')
def vehicle_info():
    return render_template('vehicleinfo.html')

@app.route('/verification')
def verification():
    return render_template('verification.html')

@app.route('/verification-alt')
def verification2():
    return render_template('verification2.html')
    
@app.route('/vehicles')
def vehicles():
    return render_template('vehicles.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')
    
@app.route('/add-vehicles')
def add_vehicles():
    return render_template('addvehicles.html')

@app.route('/profile-edit')
def profile_edit():
    return render_template('profileedit.html')
# Add these routes to app.py:
@app.route('/dashboard-main')
def dashboard_main():
    return render_template('dashboardmain.html')  # or create separate template

@app.route('/alerts')
def alerts():
    return render_template('alerts.html')  # you need this template
@app.route('/emergency')
def emergency():
    return render_template('emergency.html')  # you need this template

# --- API / Fetch Routes with Database Logic ---

# MongoDB Atlas connection
client = MongoClient("mongodb+srv://Nithish:1234@cluster0.vbqymep.mongodb.net/?retryWrites=true&w=majority")
db = client.GeoTrack
users = db.user_info
vehicles = db.vehicle_info
vehicle_tracking = db.vehicle   # stores live tracking info

# Registration endpoint
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    if not email or not password:
        return jsonify({"message": "All fields are required"}), 400

    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    if users.find_one({"email": email}):
        return jsonify({"message": "Email already exists"}), 400

    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    result=users.insert_one({"email": email, "password": hashed_pw.decode("utf-8")})

    return jsonify({"message": "Account created successfully!", "_id": str(result.inserted_id)}), 201

# Personal Information 
@app.route("/save_personalinfo", methods=["POST"])
def save_personalinfo():
    data = request.json
    _id = data.get("id")
    fullname = data.get("fullname")
    dob = data.get("dob")
    phone = data.get("phone")

    if not _id:
        return jsonify({"message": "Id is required"}), 400

    result = users.update_one(
        {"_id": ObjectId(_id)},
        {"$set": {"fullname": fullname, "dob": dob, "phone": phone}}
    )

    if result.matched_count == 0:
        return jsonify({"message": "User not found"}), 404

    return jsonify({"message": "Personal information saved successfully"}), 200

# Vehicle Information
@app.route("/save_vehicle", methods=["POST"])
def save_vehicle():
    try:
        data = request.json
        _id = data.get("id")

        if not _id:
            return jsonify({"success": False, "message": "Id is required"}), 400

        vehicles.insert_one({
            "userId": ObjectId(_id),
            "vehicleType": data.get("vehicleType"),
            "vehicleNumber": data.get("vehicleNumber"),
            "licenseNumber": data.get("licenseNumber"), 
            "aadhar": data.get("aadhar")
        })

        return jsonify({"success": True, "message": "Vehicle info saved successfully"}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# Twilio config
TWILIO_ACCOUNT_SID = "AC1bb115b1fcf15dd067ae918f2121564a"
TWILIO_AUTH_TOKEN = "e104bc876f9c25db1bfc070529338f65"
TWILIO_PHONE_NUMBER = "+14696544225"
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

otp_store = {}  # key: userId, value: otp

@app.route("/send_otp", methods=["POST"])
def send_otp():
    data = request.json
    phone = data.get("phone")
    userId = data.get("userId")

    if not phone or not userId:
        return jsonify({"success": False, "message": "Phone or userId missing"}), 400

    otp = str(random.randint(100000, 999999))
    otp_store[userId] = otp

    try:
        message = twilio_client.messages.create(
            body=f"Your OTP for vehicle verification is {otp}",
            from_=TWILIO_PHONE_NUMBER,
            to=phone
        )
        return jsonify({"success": True, "message": "OTP sent successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.json
    userId = data.get("userId")
    otp_input = data.get("otp")
    vehicle_info = data.get("vehicleInfo")

    if not userId or not otp_input or not vehicle_info:
        return jsonify({"success": False, "message": "Missing data"}), 400

    if otp_store.get(userId) != otp_input:
        return jsonify({"success": False, "message": "Invalid OTP"}), 400

    vehicles.insert_one({
        "userId": ObjectId(userId),
        **vehicle_info
    })

    otp_store.pop(userId, None)

    return jsonify({"success": True, "message": "Vehicle info saved successfully"})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"}), 400

    user = users.find_one({"email": email})
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    # ✅ CORRECTED CODE:
    stored_password = user.get("password", "")
    if not stored_password or not bcrypt.checkpw(password.encode("utf-8"), stored_password.encode("utf-8")):
        return jsonify({"success": False, "message": "Invalid password"}), 401


    return jsonify({
        "success": True,
        "message": "Login successful",
        "userId": str(user["_id"]),
        "email": user["email"]
    }), 200

@app.route("/get_user_details", methods=["POST"])
def get_user_details():
    data = request.get_json()
    userId = data.get("userId")

    if not userId:
        return jsonify({"success": False, "message": "UserId required"}), 400

    user = users.find_one({"_id": ObjectId(userId)})
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    vehicle = vehicles.find_one({"userId": ObjectId(userId)})

    return jsonify({
    "success": True,
    "fullname": user.get("fullname"),
    "phone": user.get("phone"),
    "city": user.get("city"),
    "vehicleNumber": vehicle.get("vehicleNumber") if vehicle else None,
    "vehicleType": vehicle.get("vehicleType") if vehicle else None,
    "licenseNumber": vehicle.get("licenseNumber") if vehicle else None
}),200

@app.route("/get_user_personal_details", methods=["POST"])
def get_personal_details():
    data = request.get_json()
    userId = data.get("userId")

    if not userId:
        return jsonify({"success": False, "message": "UserId required"}), 400

    user = users.find_one({"_id": ObjectId(userId)})
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    vehicle = vehicles.find_one({"userId": ObjectId(userId)})

    return jsonify({
        "success": True,
        "email" : user.get("email"),
        "fullname": user.get("fullname"),
        "phone": user.get("phone"),
        "dob": user.get("dob"),
        "aadhar" : vehicle.get("aadhar") if vehicle else None
    }), 200


@app.route("/get_vehicles", methods=["POST"])
def get_vehicles():
    data = request.get_json()
    user_id = data.get("userId")
    
    # This should probably fetch from the database, but keeping your dummy data for now
    vehicles_list = [
        {"vehicleType": "Car", "vehicleNumber": "AP00B0001"},
        {"vehicleType": "Truck", "vehicleNumber": "AP00B0011"}
    ]

    return jsonify({"success": True, "vehicles": vehicles_list})

@app.route('/update_vehicle_status', methods=['POST'])
def update_vehicle_status():
    data = request.json
    userId = data.get("userId")
    speed = data.get("speed")
    location = data.get("location")
    datetime = data.get("datetime")
    active = data.get("active", True)

    user = users.find_one({"_id": ObjectId(userId)})
    vehicle = vehicles.find_one({"userId": ObjectId(userId)})

    db.vehicle_status.update_one(
        {"userId": userId},
        {"$set": {
            "vehicleType": vehicle.get("vehicleType") if vehicle else None,
            "vehicleNumber": vehicle.get("vehicleNumber") if vehicle else None,
            "speed": speed,
            "location": location,
            "time": datetime,
            "active": active
        }},
        upsert=True
    )

    return jsonify({"success": True})

@app.route("/set_active_status", methods=["POST"])
def set_active_status():
    try:
        data = request.json
        userId = data.get("userId")
        active = data.get("active")

        if not userId:
            return jsonify({"success": False, "message": "Missing userId"}), 400

        vehicle_tracking.update_one(
            {"userId": ObjectId(userId)},
            {"$set": {"active": active}},
            upsert=True
        )

        return jsonify({"success": True, "message": "Active status updated"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c


@app.route('/get_nearby_vehicles', methods=['POST'])
def get_nearby_vehicles():
    data = request.json
    userId = data.get("userId")

    me = db.vehicle_status.find_one({"userId": userId, "active": True})
    if not me or "location" not in me:
        return jsonify({"success": False, "msg": "No location for user"})

    my_loc = me["location"]

    nearby = []
    for other in db.vehicle_status.find({"userId": {"$ne": userId}, "active": True}):
        if "location" not in other: 
            continue
        dist = haversine(my_loc["lat"], my_loc["lng"],
                         other["location"]["lat"], other["location"]["lng"])
        if dist <= 1.5:
            nearby.append({
                "vehicleType": other.get("vehicleType"),
                "vehicleNumber": other.get("vehicleNumber"),
                "speed": other.get("speed"),
                "location": other.get("location"),
                "time": other.get("time")
            })

    return jsonify({"success": True, "nearby": nearby})
@app.route("/make_emergency_call", methods=["POST"])
def make_emergency_call():
    try:
        data = request.json
        userId = data.get("userId")

        if not userId:
            return jsonify({"success": False, "message": "UserId required"}), 400

        # Fetch user phone from database
        user = users.find_one({"_id": ObjectId(userId)})
        if not user or "phone" not in user:
            return jsonify({"success": False, "message": "Phone number not found"}), 404

        phone_number = user["phone"]

        # Place a call using Twilio
        call = twilio_client.calls.create(
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
            twiml='<Response><Say voice="alice">This is an emergency alert. Please respond immediately.</Say></Response>'
        )

        return jsonify({"success": True, "sid": call.sid})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
if __name__ == "__main__":
    app.run(debug=True)