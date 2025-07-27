from flask import Flask,render_template,request,redirect,url_for,session,flash
from models import db, Users, Parking_Lots, Parking_Spots, Reserve
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import datetime,timezone, timedelta
import math, os
import matplotlib.pyplot as plt
IST = timezone(timedelta(hours=5, minutes=30))

app = Flask(__name__)

app.config['SECRET_KEY']='pass@123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def home():
      return render_template('home.html')


@app.route('/register',methods=['GET','POST'])
def register():
	if request.method=='POST':
		full_name=request.form['full_name']
		email=request.form['email']
		password=request.form['password']
		role=request.form.get('role','user')
		
		new_user=Users(full_name=full_name, email=email, 
				password=generate_password_hash(password),
				role=role)
		
		db.session.add(new_user)
		db.session.commit()
		
		return redirect(url_for('login'))
	
	return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = Users.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.user_id
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'user':
                return redirect(url_for('user_dashboard'))
            else:
                flash("Invalid user role.")
                return redirect(url_for('login'))
        else:
            flash("Invalid email or password. Please try again.")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    current_user = Users.query.filter_by(user_id=session['user_id']).first()
    if not current_user or current_user.role != 'admin':
        return redirect(url_for('login'))  
    
    reservations = Reserve.query.all()

    users = Users.query.all()
    lots = Parking_Lots.query.all()
    return render_template('admin_dashboard.html', users=users, lots=lots, reservations=reservations)

@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = Users.query.filter_by(user_id=session['user_id']).first()
    if not current_user or current_user.role != 'user':
        return redirect(url_for('login'))
    

    reservations = Reserve.query.filter_by(user_id=current_user.user_id).all()
    

    for reservation in reservations:
        spot = Parking_Spots.query.filter_by(spot_id=reservation.parking_spot_id, status='R').first()
        if spot:
            reservation.spot_id = spot.spot_id
        else:
            reservation.spot_id = None
    
    return render_template('user_dashboard.html', reservations=reservations) 


@app.route('/add_parking_lots', methods=['GET', 'POST'])
def add_parking_lot():
    if request.method == 'POST':
        prime_location = request.form.get('prime_location')
        address = request.form['address']
        pincode = request.form['pincode']
        price = request.form['price']
        spots = request.form['spots']

        new_parking_lot = Parking_Lots(
            prime_location_name=prime_location,
            address=address,
            pincode=pincode,
            price=price,
            max_spot=spots
        )

        db.session.add(new_parking_lot)
        db.session.commit()

        for i in range(int(spots)):
            spot_id = str(new_parking_lot.lot_id) + str(i)
            new_spot = Parking_Spots(
                spot_id=spot_id,
                parking_lot_id=new_parking_lot.lot_id  
            )
            db.session.add(new_spot)

        db.session.commit()  

        return redirect(url_for('add_parking_lot'))

    return render_template('add_parking_lots.html')



@app.route('/edit_parking_lots/<int:lot_id>', methods=['GET', 'POST'])
def edit_parking_lot(lot_id):
    lot = Parking_Lots.query.get_or_404(lot_id)
    spots = Parking_Spots.query.filter_by(parking_lot_id=lot_id).all()
    user_id = session.get('user_id')
    user = Users.query.get(user_id)
    if not user or (user.role != 'admin' and lot.user_id != user_id):
        flash("You don't have permission to edit this parking lot.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        lot.prime_location_name = request.form.get('prime_location')
        lot.address = request.form.get('address')
        lot.pincode = request.form.get('pincode')
        new_max_spots = request.form.get('spots')
        price = request.form.get('price')

        old_max_spots=int(lot.max_spot)
        new_max_spots=int(new_max_spots)


        try:
            price = float(price)
            if price < 0:
                flash("Price must be a positive number.", "danger")
                return render_template('edit_parking_lots.html', parking_lot=lot)
        except (ValueError, TypeError):
            flash("Price must be a valid positive number.", "danger")
            return render_template('edit_parking_lots.html', parking_lot=lot)

        lot.price = price

        if new_max_spots>old_max_spots:
            for i in range(old_max_spots, new_max_spots):
                new_slot= Parking_Spots(spot_id= str(lot.lot_id)+str(i), status='A', parking_lot_id=lot.lot_id)
                db.session.add(new_slot)

        elif new_max_spots < old_max_spots:
            slots_to_delete = Parking_Spots.query.filter_by(parking_lot_id=lot.lot_id)\
                .order_by(Parking_Spots.spot_id.desc())\
                .limit(old_max_spots - new_max_spots)\
                .all()
            for slot in slots_to_delete:
                db.session.delete(slot)
        
        lot.max_spot=new_max_spots


        db.session.commit()
        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('home'))

    return render_template('edit_parking_lots.html', parking_lot=lot)


@app.route('/delete_parking_lots/<int:lot_id>',methods=['POST'])
def delete_parking_lot(lot_id):
    lot = Parking_Lots.query.get_or_404(lot_id)
    spots = Parking_Spots.query.filter_by(parking_lot_id=lot_id).all()

    user_id = session.get('user_id')
    user = Users.query.get(user_id)
    if not user or (user.role != 'admin' and lot.user_id != user_id):
        flash("You don't have permission to delete this parking lot.", "danger")
        return redirect(url_for('home'))
    for spot in spots:
        if spot.status!='A':
            flash("Free up the parking before deletion.", "danger")
            return redirect(url_for('admin_dashboard'))      
    
    db.session.delete(lot)
    db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/view_parking_lot/<int:lot_id>',methods=['GET','POST'])
def view_parking_lot(lot_id):

    user_id = session.get('user_id')
    user = Users.query.get(user_id)
    parking_lot = Parking_Lots.query.get_or_404(lot_id)

    if not user or (user.role != 'admin' and parking_lot.user_id != user_id):
        flash("You don't have permission to view this parking lot.", "danger")
        return redirect(url_for('home'))
    
    spots = Parking_Spots.query.filter_by(parking_lot_id=lot_id).all()
    A = 0
    R = 0
    for spot in spots:
        if spot.status=='A':
            A+=1
        elif spot.status=='R':
            R+=1

    return render_template('view_parking_lot.html', spots=spots,lot=parking_lot,A=A,R=R)
         
@app.route('/reserve_parking', methods=['GET', 'POST'])
def reserve_parking():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = Users.query.filter_by(user_id=session['user_id']).first()
    if not current_user or current_user.role != 'user':
        flash("You don't have permission to reserve parking.", "danger")
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        lot_id = request.form.get('lot_id')
        vehicle_number = request.form.get('vehicle_number')
        
        parking_lot = Parking_Lots.query.get_or_404(lot_id)
        available_spot = Parking_Spots.query.filter_by(parking_lot_id=lot_id, status='A').first()
        
        if not available_spot:
            flash("No spots available in this parking lot.", "danger")
            return redirect(url_for('reserve_parking'))
        

        available_spot.status = 'R'
        parked_at = datetime.now(IST)      
        available_spot.parked_at=parked_at
        db.session.add(available_spot)  

        new_reservation = Reserve(
            vehicle_number=vehicle_number,
            user_id=current_user.user_id,
            parking_spot_id=available_spot.spot_id,
            parked_at=parked_at,
            released_at=None
        )

        db.session.add(new_reservation)
        db.session.commit()
        flash("Parking spot reserved successfully!", "success")
        return redirect(url_for('user_dashboard'))
    

    parking_lots = Parking_Lots.query.all()
    available_lots = []
    for lot in parking_lots:
        available_spots = Parking_Spots.query.filter_by(parking_lot_id=lot.lot_id, status='A').count()
        if available_spots > 0:
            lot.available_spots = available_spots
            available_lots.append(lot)
    
    return render_template('reserve_parking.html', lots=available_lots)

@app.route('/release_parking_spot', methods=['POST'])
def release_parking_spot():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = Users.query.filter_by(user_id=session['user_id']).first()
    if not current_user or current_user.role != 'user':
        flash("You don't have permission to release parking spots.", "danger")
        return redirect(url_for('home'))
    
    spot_id = request.form.get('spot_id')
    if not spot_id:
        flash("No parking spot specified.", "danger")
        return redirect(url_for('user_dashboard'))
    
    spot = Parking_Spots.query.get(spot_id)
    if not spot:
        flash("Parking spot not found.", "danger")
        return redirect(url_for('user_dashboard'))
    if spot.status != 'R':
        flash("This spot is not currently reserved.", "danger")
        return redirect(url_for('user_dashboard'))


    reservation = Reserve.query.filter_by(
        parking_spot_id=spot.spot_id,
        user_id=current_user.user_id,
        released_at=None
    ).order_by(Reserve.parked_at.desc()).first()
    if not reservation:
        flash("You don't have an active reservation for this spot.", "danger")
        return redirect(url_for('user_dashboard'))
    
    lot=Parking_Lots.query.filter_by(lot_id=spot.parking_lot_id).first()
    release_time = datetime.now(IST)
    spot.status = 'A'
    spot.parked_at = None
    reservation.released_at = release_time
    end = datetime.fromisoformat(str(reservation.released_at))
    start = datetime.fromisoformat(str(reservation.parked_at)+"+05:30")
    duration=end-start
    minutes = duration.total_seconds() / 60
    cost=math.ceil(lot.price*minutes)
    minutes=math.ceil(minutes)
    reservation.total_time=minutes
    reservation.total_cost=cost

    db.session.add(spot)
    db.session.add(reservation)
    db.session.commit()
    message = "Total Cost: Rs. " + str(cost) + "  " + "Total Time: " + str(minutes) + " min"
    flash("Parking spot released successfully!", "success")
    flash(message, "danger")
    return redirect(url_for('user_dashboard'))

@app.route('/admin_summary_chart')
def admin_summary_charts():
    spots = Parking_Spots.query.all()
    lots = Parking_Spots.query.all()
    reservations = Reserve.query.all()

    lot_price_map = {}
    prime_locations = {}

    for res in reservations:
        if res.released_at!=None:
            spot_id = res.parking_spot
            price = res.total_cost
            prime_location= spot_id.parking_lot.prime_location_name

            if prime_location in lot_price_map:
                lot_price_map[prime_location] += price
            else:
                lot_price_map[prime_location] = price

    locations = list(lot_price_map.keys())
    prices = list(lot_price_map.values())

    print(locations,prices)

    fig, ax = plt.subplots(figsize=(10, 6), facecolor='none')

    bars = ax.bar(locations, prices, color='darkgrey', alpha=0.7)

    ax.patch.set_alpha(0.15)

    ax.set_xlabel('Location', color='white', labelpad=25, fontstyle='italic')
    ax.set_ylabel('Revenue', color='white', labelpad=25, fontstyle='oblique')
    ax.set_title('Revenue Summary (in Rs.)', color='white', fontweight='bold')
    ax.tick_params(axis='x', rotation=45, labelcolor='white')
    ax.tick_params(axis='y', labelcolor='white')

    plt.xticks(rotation=45, ha='right')

    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height / 2, 
            f'{height}',
            ha='center',
            va='center',
            color='black',
            fontweight='bold'
        )

    plt.tight_layout()

    plt.subplots_adjust(left=0.2, right=0.8)

    charts_folder = os.path.join(app.root_path, 'static', 'charts')
    os.makedirs(charts_folder, exist_ok=True)

    chart_path = os.path.join(charts_folder, 'admin_summary.png')
    plt.savefig(chart_path)
    plt.close()

    return render_template('admin_summary_chart.html',chart_url=url_for('static', filename='charts/admin_summary.png'))


@app.route('/user_summary_chart')
def user_summary_charts():
    spots = Parking_Spots.query.all()
    lots = Parking_Spots.query.all()
    current_user = Users.query.filter_by(user_id=session['user_id']).first()
    reservations = Reserve.query.filter_by(user_id=session['user_id']).all()

    lot_time_map = {}
    prime_locations = {}

    for res in reservations:
        if res.released_at!=None:
            spot_id = res.parking_spot
            time = res.total_time
            prime_location= spot_id.parking_lot.prime_location_name

            if prime_location in lot_time_map:
                lot_time_map[prime_location] += time
            else:
                lot_time_map[prime_location] = time

    locations = list(lot_time_map.keys())
    time = list(lot_time_map.values())

    for i in range(0,len(time)):
        time[i]=math.ceil(time[i]/60)

    fig, ax = plt.subplots(figsize=(10, 6), facecolor='none')

    bars = ax.bar(locations, time, color='darkgrey', alpha=0.7)

    ax.patch.set_alpha(0.15)

    ax.set_xlabel('Location', color='white', labelpad=25, fontstyle='italic')
    ax.set_ylabel('Hours', color='white', labelpad=25, fontstyle='oblique')
    ax.set_title('Parking Summary (in hrs.)', color='white', fontweight='bold')
    ax.tick_params(axis='x', rotation=45, labelcolor='white')
    ax.tick_params(axis='y', labelcolor='white')

    plt.xticks(rotation=45, ha='right')

    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height / 2, 
            f'{height}',
            ha='center',
            va='center',
            color='black',
            fontweight='bold'
        )

    plt.tight_layout()

    plt.subplots_adjust(left=0.2, right=0.8)

    charts_folder = os.path.join(app.root_path, 'static', 'charts')
    os.makedirs(charts_folder, exist_ok=True)

    chart_path = os.path.join(charts_folder, 'user_summary.png')
    plt.savefig(chart_path)
    plt.close()

    return render_template('user_summary_chart.html',chart_url=url_for('static', filename='charts/user_summary.png'))


def initialize_admin():
    with app.app_context():
        if not Users.query.filter_by(role='admin').first():
            admin = Users(full_name='Yash',  
                        email='admin@gmail.com',  
                        password=generate_password_hash('admin'), 
                        role='admin')
            db.session.add(admin)
            db.session.commit()
	
	
with app.app_context():
    db.create_all()

if __name__ == '__main__':
	initialize_admin()
	app.run()