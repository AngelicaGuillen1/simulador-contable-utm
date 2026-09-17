# Register and export all blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.accounting import accounting_bp
from routes.sales import sales_bp
from routes.purchases import purchases_bp
from routes.inventory import inventory_bp
from routes.treasury import treasury_bp
from routes.partners import partners_bp
from routes.financial_statements import financial_bp
from routes.simulations import simulations_bp
from routes.tutor import tutor_bp
from routes.reports import reports_bp
from routes.admin import admin_bp
from routes.api import api_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(accounting_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(treasury_bp)
    app.register_blueprint(partners_bp)
    app.register_blueprint(financial_bp)
    app.register_blueprint(simulations_bp)
    app.register_blueprint(tutor_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
