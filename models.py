from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint

db = SQLAlchemy()

class Users(db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False, default="user")
    
    reservations = db.relationship(
        "Reserve",
        backref="user",
        cascade="all, delete-orphan"
    )

class Parking_Lots(db.Model):
    __tablename__ = "parking_lots"
    lot_id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String, nullable=False)
    address = db.Column(db.String, unique=True, nullable=False)
    pincode = db.Column(db.String, nullable=False)
    max_spot = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Integer, nullable=False)
    __table_args__ = (CheckConstraint('max_spot>0', name='check_spot'),)

    spots = db.relationship(
        "Parking_Spots",
        backref="parking_lot",
        cascade="all, delete-orphan"
    )

class Parking_Spots(db.Model):
    __tablename__ = "parking_spots"
    spot_id = db.Column(db.Integer, primary_key=True)
    parked_at = db.Column(db.DateTime, nullable=True)
    released_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String, nullable=False, default='A')
    parking_lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.lot_id'))

    reservations = db.relationship(
        "Reserve",
        backref="parking_spot",
        cascade="all, delete-orphan"
    )

class Reserve(db.Model):
    __tablename__ = "reserve"
    reserve_id = db.Column(db.Integer, primary_key=True)
    vehicle_number = db.Column(db.String, nullable=False)
    parked_at = db.Column(db.DateTime)
    released_at = db.Column(db.DateTime)
    total_time = db.Column(db.Integer)
    total_cost = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    parking_spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.spot_id'))

