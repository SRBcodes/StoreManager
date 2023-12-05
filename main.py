# main.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import request, jsonify, make_response
# from models import Department, Item, Inventory
from sqlalchemy.exc import IntegrityError, NoResultFound

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:pass123@localhost/department_store'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Department(db.Model):
    __tablename__ = 'department'
    dept_id = db.Column(db.Integer, primary_key=True)
    dept_name = db.Column(db.String(100), nullable=False, unique=True)
    items = db.relationship('Item', backref='department', lazy=True)

class Item(db.Model):
    __tablename__ = 'item'
    item_id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    dept_id = db.Column(db.Integer, db.ForeignKey('department.dept_id'), nullable=False)

class Inventory(db.Model):
    __tablename__ = 'inventory'
    item_id = db.Column(db.Integer, db.ForeignKey('item.item_id'), primary_key=True)
    dept_id = db.Column(db.Integer, db.ForeignKey('department.dept_id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)



# Import routes after creating the app and db instances to avoid circular imports

@app.route('/inventory', methods=['POST'])
def add_item_to_inventory():
    data = request.get_json()
    
    # Input validation (ensure all required fields are provided)
    if not data or 'item_id' not in data or 'dept_id' not in data or 'quantity' not in data:
        return make_response(jsonify({'error': 'Missing data'}), 400)

    try:
        # Check if the item and department exist, if not throw an error
        item = Item.query.filter_by(item_id=data['item_id']).one_or_none()
        dept = Department.query.filter_by(dept_id=data['dept_id']).one_or_none()

        if item is None or dept is None:
            return make_response(jsonify({'error': 'Invalid item_id or dept_id'}), 400)

        # Check if the inventory record already exists
        inventory = Inventory.query.filter_by(item_id=data['item_id'], dept_id=data['dept_id']).one_or_none()

        if inventory:
            # Inventory record exists, add to the current quantity
            inventory.quantity += data['quantity']  # Add the new quantity to existing quantity
        else:
            # No record exists, so create a new one
            new_inventory = Inventory(item_id=data['item_id'], dept_id=data['dept_id'], quantity=data['quantity'])
            db.session.add(new_inventory)

        # Commit the changes
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return make_response(jsonify({'error': 'Database Integrity Error - Possibly duplicate entry or invalid data'}), 400)

    # Return a success response
    return make_response(jsonify({
        "item_id": data['item_id'],
        "message": "Item successfully added to inventory",
        "quantity": inventory.quantity
    }), 200)


@app.route('/department/<int:dept_id>/inventory', methods=['GET'])
def get_department_inventory(dept_id):
    # Check if the department exists
    department = Department.query.filter_by(dept_id=dept_id).first()
    if department is None:
        return make_response(jsonify({'error': 'Department not found'}), 404)

    # If the department exists, query for its inventory
    inventory = db.session.query(Item, Inventory).join(Inventory, Item.item_id == Inventory.item_id).filter(Item.dept_id == dept_id).all()

    # Check if the inventory is empty
    if not inventory:
        return make_response(jsonify({'error': 'No inventory available for this department'}), 404)

    # If inventory items are found, process them into the response
    results = [
        {"item_id": item.item_id, "item_name": item.item_name, "quantity": inv.quantity}
        for item, inv in inventory
    ]

    return jsonify(results)



def create_app():
    with app.app_context():
        db.create_all()  # Creates defined tables in the database
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
