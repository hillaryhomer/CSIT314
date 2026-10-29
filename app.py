from flask import Flask, render_template, request, redirect, url_for, session

# 1. Define 'app' FIRST
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for session management

class InteriorDesignerProfile:

    profiles_db = []

    def __init__(self, name, email):
        self.designerID = "ID" + str(len(InteriorDesignerProfile.profiles_db) + 1)
        self.name = name
        self.email = email
        InteriorDesignerProfile.profiles_db.append(self)

@app.route('/designer/register', methods=['GET', 'POST'])
def register_profile():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        
        # Create profile
        new_profile = InteriorDesignerProfile(name, email)
        
        # Save designerID in session so company creation knows who owns it
        session['user_id'] = new_profile.designerID
        session['is_authenticated'] = True
        
        # Redirect directly to your company creation page!
        return redirect(url_for('open_form'))
        
    return render_template('register_profile.html')


# ==========================================
# 2. COMPANY INFORMATION ENTITY
# ==========================================
class CompanyInformation:
    db_storage = []

    def __init__(self, name, reg_number, address, contact, description, owner_id):
        self.company_id = len(CompanyInformation.db_storage) + 1
        self.name = name
        self.regNumber = reg_number
        self.address = address
        self.contact = contact
        self.description = description
        self.owner_id = owner_id

    @classmethod
    def validate_references(cls, name, reg_number, owner_id):
        for company in cls.db_storage:
            if company.regNumber == reg_number:
                return False, "Duplicate Business Registration Number already registered."
            if company.name.lower() == name.lower() and company.owner_id == owner_id:
                return False, "Duplicate company name already registered for this user."
        return True, None

    @classmethod
    def create(cls, details, owner_id):
        try:
            new_company = cls(
                name=details['name'],
                reg_number=details['regNumber'],
                address=details['address'],
                contact=details['contact'],
                description=details['description'],
                owner_id=owner_id
            )
            cls.db_storage.append(new_company)
            return {"status": "success", "record": new_company}
        except Exception as e:
            return {"status": "failure", "error": str(e)}


# ==========================================
# 3. COMPANY INFORMATION CONTROLLER
# ==========================================
class CreateCompanyInformationController:
    def create_company_information(self, details, context):
        user_id = context.get('user_id')
        is_authenticated = context.get('is_authenticated', False)
        
        if not is_authenticated or not user_id:
            return {"success": False, "error": "Unauthorized access. Please register your profile first."}
        
        if not details.get('name') or not details.get('regNumber') or not details.get('address') or not details.get('contact'):
            return {"success": False, "error": "All required fields must be filled out."}

        is_valid, ref_error = CompanyInformation.validate_references(details['name'], details['regNumber'], user_id)
        if not is_valid:
            return {"success": False, "error": ref_error}

        result = CompanyInformation.create(details, user_id)
        
        if result["status"] == "success":
            return {"success": True, "record": result["record"]}
        else:
            return {"success": False, "error": "Storage failure: Unable to save record to database."}


# ==========================================
# 4. COMPANY INFORMATION BOUNDARY & ROUTES
# ==========================================
@app.route('/company/create', methods=['GET'])
def open_form():
    # If a user tries to access this directly without registering first, redirect them
    if not session.get('is_authenticated'):
        return redirect(url_for('register_profile'))
        
    return render_template('create_company.html', error=None, success=None)

@app.route('/company/create', methods=['POST'])
def submit_form():
    details = {
        'name': request.form.get('name'),
        'regNumber': request.form.get('regNumber'),
        'address': request.form.get('address'),
        'contact': request.form.get('contact'),
        'description': request.form.get('description')
    }
    
    context = {
        'user_id': session.get('user_id'),
        'is_authenticated': session.get('is_authenticated', False)
    }

    controller = CreateCompanyInformationController()
    response = controller.create_company_information(details, context)

    if response["success"]:
        record = response["record"]
        return render_template('create_company.html', success=f"Company '{record.name}' created successfully!", record=record, error=None)
    else:
        return render_template('create_company.html', error=response["error"], success=None, form_data=details)


if __name__ == '__main__':
    app.run(debug=True)