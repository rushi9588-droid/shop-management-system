from flask import Flask, render_template, request, redirect, url_for, send_file
from config import connection
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.units import mm
import os
import logging
from datetime import datetime
import mysql.connector


def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="shop_management"
    )


app = Flask(__name__)

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==========================================
# CONTEXT PROCESSOR
# ==========================================

@app.context_processor
def inject_today_expenses():

    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE expense_date = CURDATE()
    """)

    expenses_total = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM customers
        WHERE customer_date = CURDATE()
    """)

    customers_total = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM sales
        WHERE sale_date = CURDATE()
    """)

    sales_total = cursor.fetchone()["total"]

    cursor.close()

    return {
        "expenses": expenses_total,
        "customers": customers_total,
        "sales": sales_total
    }


# ==========================================
# GENERATE BILL PDF
# ==========================================

def generate_bill_pdf(bill_id):

    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM createbill
        WHERE bill_id = %s
    """, (bill_id,))

    bill = cursor.fetchone()

    cursor.close()

    if not bill:
        return None

    pdf_folder = "static/bills"

    if not os.path.exists(pdf_folder):
        os.makedirs(pdf_folder)

    pdf_path = os.path.join(
        pdf_folder,
        f"bill_{bill_id}.pdf"
    )

    document = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ShopTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=22,
        spaceAfter=5
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=10,
        textColor=colors.grey
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=11
    )

    content = []

    content.append(Paragraph("BEST SELECTION", title_style))
    content.append(Paragraph("SHOP MANAGEMENT SYSTEM", subtitle_style))
    content.append(Spacer(1, 10))

    bill_info = [
        [
            Paragraph("<b>Bill No.</b>", styles["Normal"]),
            str(bill["bill_id"]),
            Paragraph("<b>Date</b>", styles["Normal"]),
            bill["bill_date"].strftime("%d-%m-%Y") if bill["bill_date"] else ""
        ],
        [
            Paragraph("<b>Customer Name:</b>", styles["Normal"]),
            str(bill["name"] or ""),
            Paragraph("<b>Mobile No:</b>", styles["Normal"]),
            str(bill["mobile_no"] or "")
        ],
        [
            Paragraph("<b>City:</b>", styles["Normal"]),
            str(bill["city"] or ""),
            Paragraph("<b>Customer ID:</b>", styles["Normal"]),
            str(bill["customer_id"] or "")
        ]
    ]

    info_table = Table(bill_info, colWidths=[30 * mm, 55 * mm, 30 * mm, 55 * mm])

    info_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("BACKGROUND", (2, 0), (2, -1), colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 7)
    ]))

    content.append(info_table)
    content.append(Spacer(1, 15))

    products_text = str(bill["products"] or "")
    prices_text = str(bill["price"] or "")

    products = [p.strip() for p in products_text.split(",") if p.strip()]
    prices = [p.strip() for p in prices_text.split(",") if p.strip()]

    product_data = [["Sr. No.", "Product", "Amount"]]

    subtotal = 0

    for i, product in enumerate(products):

        if i < len(prices):
            try:
                product_price = float(prices[i])
            except (ValueError, TypeError):
                product_price = 0
        else:
            product_price = 0

        subtotal += product_price

        product_data.append([str(i + 1), product, f"₹{product_price:.2f}"])

    try:
        discount = float(bill["discount"] or 0)
    except (ValueError, TypeError):
        discount = 0

    if discount < 0:
        discount = 0

    if discount > subtotal:
        discount = subtotal

    grand_total = subtotal - discount

    if grand_total < 0:
        grand_total = 0

    product_data.append(["", "SUBTOTAL", f"{subtotal:.2f}"])
    product_data.append(["", "DISCOUNT", f"- {discount:.2f}"])
    product_data.append(["", "GRAND TOTAL", f"{grand_total:.2f}"])

    product_table = Table(product_data, colWidths=[25 * mm, 105 * mm, 40 * mm])

    product_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.7, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
        ("FONTNAME", (1, -3), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 8)
    ]))

    content.append(product_table)
    content.append(Spacer(1, 20))

    content.append(Paragraph("Thank You For Shopping With Us!", footer_style))

    document.build(content)

    return pdf_path


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/")
@app.route("/dashboard")
def dashboard():

    return render_template("dashboard.html", bills_count=0)


# ==========================================
# CREATE BILL - SHOW PAGE
# ==========================================

@app.route("/createbill", methods=["GET"])
def createbill_page():

    return render_template("createbill.html")


# ==========================================
# CREATE BILL - SAVE DATA
# ==========================================

@app.route("/createbill", methods=["POST"])
def createbill():

    name = request.form.get("name")
    city = request.form.get("city")
    mobile_no = request.form.get("mobile_no")

    products = request.form.get("products")
    price = request.form.get("price")

    bill_date = request.form.get("bill_date")

    discount = request.form.get("discount")

    if not name or not products or not price:
        return ("Missing required fields: name, products and price are required.", 400)

    try:
        price_list = [p.strip() for p in price.split(",") if p.strip() != ""]

        subtotal = sum(float(p) for p in price_list)

        discount = float(discount or 0)

        if discount < 0:
            discount = 0

        if discount > subtotal:
            discount = subtotal

        total = subtotal - discount

        if total < 0:
            total = 0

    except (ValueError, TypeError):
        return ("Invalid price or discount value submitted.", 400)

    logger.info(
        "Bill submission received | name=%s city=%s mobile=%s products=%s price=%s subtotal=%s discount=%s total=%s date=%s",
        name, city, mobile_no, products, price, subtotal, discount, total, bill_date
    )

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT COALESCE(MAX(customer_id), 0) + 1
            FROM createbill
        """)

        customer_id = cursor.fetchone()[0]

        sql = """
            INSERT INTO createbill
            (customer_id, name, city, mobile_no, products, price, total, bill_date, discount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (customer_id, name, city, mobile_no, products, price, total, bill_date, discount)

        cursor.execute(sql, values)

        bill_id = cursor.lastrowid

        # ==========================================
        # AUTO-ADD CUSTOMER
        # ==========================================

        customer_sql = """
            INSERT INTO customers (name, mobile_no, city)
            VALUES (%s, %s, %s)
        """

        cursor.execute(customer_sql, (name, mobile_no, city))

        # ==========================================
        # AUTO-ADD SALE
        # ==========================================

        sales_sql = """
            INSERT INTO sales (customer_id, name, amount)
            VALUES (%s, %s, %s)
        """

        cursor.execute(sales_sql, (customer_id, name, total))

        # ==========================================
        # UPDATE TOTAL AMOUNT
        # One row per day: today's Sales minus today's
        # Expenses. Recalculated on every new bill so
        # it always stays accurate.
        # ==========================================

        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM sales
            WHERE sale_date = CURDATE()
        """)

        day_sales = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM expenses
            WHERE expense_date = CURDATE()
        """)

        day_expenses = cursor.fetchone()[0]

        day_net = day_sales - day_expenses

        cursor.execute("""
            INSERT INTO total_amount (total_date, amount)
            VALUES (CURDATE(), %s)
            ON DUPLICATE KEY UPDATE amount = %s
        """, (day_net, day_net))

        connection.commit()

        cursor.close()

        pdf_path = generate_bill_pdf(bill_id)

        logger.info(
            "Bill saved successfully | bill_id=%s customer_id=%s pdf=%s",
            bill_id, customer_id, pdf_path
        )

        return send_file(pdf_path, as_attachment=True, download_name=f"bill_{bill_id}.pdf")

    except Exception as e:

        connection.rollback()

        logger.exception("Error while saving bill")

        return ("Something went wrong while saving the bill. Please try again.", 500)


# ==========================================
# EXPENSES
# ==========================================

@app.route("/expenses", methods=["GET", "POST"])
def expenses():

    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        name = request.form.get("name")
        amount = request.form.get("amount")

        if not name or not amount:
            cursor.close()
            return ("Missing required fields: name and amount are required.", 400)

        try:
            amount = float(amount)
        except ValueError:
            cursor.close()
            return ("Invalid amount value.", 400)

        try:
            query = """
                INSERT INTO expenses (name, amount)
                VALUES (%s, %s)
            """

            cursor.execute(query, (name, amount))

            connection.commit()

        except Exception:
            connection.rollback()
            logger.exception("Error while saving expense")
            cursor.close()
            return ("Something went wrong while saving the expense. Please try again.", 500)

        cursor.close()

        return redirect("/expenses")

    cursor.execute("""
        SELECT *
        FROM expenses
        ORDER BY expense_id DESC
    """)

    expenses_data = cursor.fetchall()

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
    """)

    total_data = cursor.fetchone()

    total = total_data["total"]

    cursor.close()

    return render_template("expenses.html", expenses=expenses_data, total=total)


# ==========================================
# EXPENSES HISTORY
# ==========================================

@app.route("/expenses_history", methods=["GET"])
def expenses_history():

    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM expenses
        ORDER BY expense_id ASC
    """)

    history_data = cursor.fetchall()

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
    """)

    total_data = cursor.fetchone()

    total = total_data["total"]

    cursor.close()

    return render_template("expenses_history.html", expenses=history_data, total=total)


# ==========================================
# CUSTOMERS
# ==========================================

@app.route("/customers", methods=["GET"])
def customers():

    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM customers
        WHERE customer_date = CURDATE()
        ORDER BY customer_id DESC
    """)

    customers_data = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM customers
        WHERE customer_date = CURDATE()
    """)

    total_data = cursor.fetchone()

    total = total_data["total"]

    cursor.close()

    return render_template("customers.html", customers=customers_data, total=total)


# ==========================================
# ALL CUSTOMERS
# ==========================================

@app.route("/customer_history", methods=["GET"])
def allcustomers():

    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM customers_history
        ORDER BY history_id ASC
    """)

    customers_data = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM customers_history
    """)

    total_data = cursor.fetchone()

    total = total_data["total"]

    cursor.close()

    return render_template("customer_history.html", customers=customers_data, total=total)


# ==========================================
# SALES
# ==========================================

@app.route("/sales", methods=["GET"])
def sales():

    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM sales
        WHERE sale_date = CURDATE()
        ORDER BY sale_id DESC
    """)

    sales_data = cursor.fetchall()

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM sales
        WHERE sale_date = CURDATE()
    """)

    total_data = cursor.fetchone()

    total = total_data["total"]

    cursor.close()

    return render_template("sales.html", sales=sales_data, total=total)


# ==========================================
# SALES HISTORY
# ==========================================

@app.route("/saleshistory", methods=["GET"])
def saleshistory():

    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM sales_history
        ORDER BY history_id ASC
    """)

    sales_data = cursor.fetchall()

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM sales_history
    """)

    total_data = cursor.fetchone()

    total = total_data["total"]

    cursor.close()

    return render_template("sales_history.html", sales=sales_data, total=total)


# ==========================================
# TOTAL AMOUNT (date range: Sales - Expenses)
# Defaults to the last 3 days if no range is picked
# ==========================================

@app.route("/total_amount", methods=["GET"])
def total_amount():

    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")

    if not from_date or not to_date:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT DATE_SUB(CURDATE(), INTERVAL 2 DAY), CURDATE()
        """)

        from_date, to_date = cursor.fetchone()

        cursor.close()

    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM sales_history
        WHERE sale_date BETWEEN %s AND %s
    """, (from_date, to_date))

    range_sales = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE expense_date BETWEEN %s AND %s
    """, (from_date, to_date))

    range_expenses = cursor.fetchone()["total"]

    cursor.close()

    range_total = range_sales - range_expenses

    return render_template(
        "total_amount.html",
        from_date=from_date,
        to_date=to_date,
        range_sales=range_sales,
        range_expenses=range_expenses,
        range_total=range_total
    )


# ==========================================
# ALL BILLS
# ==========================================

@app.route("/allbills", methods=["GET"])
def allbills():

    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT bill_id, customer_id, name, city, bill_date
        FROM createbill
        ORDER BY bill_id DESC
    """)

    bills_data = cursor.fetchall()

    cursor.close()

    return render_template("allbills.html", bills=bills_data)


# ==========================================
# SUPPLIERS
# ==========================================

@app.route("/suppliers", methods=["GET", "POST"])
def suppliers():

    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        name = request.form.get("name")

        if not name:
            cursor.close()
            return ("Missing required field: name.", 400)

        try:
            cursor.execute("""
                INSERT INTO suppliers (name, amount)
                VALUES (%s, 0)
            """, (name,))

            connection.commit()

        except Exception:
            connection.rollback()
            logger.exception("Error while adding supplier")
            cursor.close()
            return ("Something went wrong while adding the supplier.", 500)

        cursor.close()

        return redirect("/suppliers")

    cursor.execute("""
        SELECT supplier_id, name, amount
        FROM suppliers
        ORDER BY supplier_id ASC
    """)

    suppliers_data = cursor.fetchall()

    cursor.close()

    return render_template("suppliers.html", suppliers=suppliers_data)


# ==========================================
# SUPPLIER DETAIL
# ==========================================

@app.route("/supplier_detail/<int:supplier_id>", methods=["GET", "POST"])
def supplier_detail(supplier_id):

    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        description = request.form.get("description")

        debit = request.form.get("debit") or 0
        credit = request.form.get("credit") or 0

        try:
            debit = float(debit)
            credit = float(credit)
        except ValueError:
            cursor.close()
            return ("Invalid debit/credit value.", 400)

        try:
            cursor.execute("""
                INSERT INTO supplier_transactions
                (supplier_id, description, debit, credit)
                VALUES (%s, %s, %s, %s)
            """, (supplier_id, description, debit, credit))

            cursor.execute("""
                UPDATE suppliers
                SET amount = amount + %s - %s
                WHERE supplier_id = %s
            """, (credit, debit, supplier_id))

            connection.commit()

        except Exception:
            connection.rollback()
            logger.exception("Error while adding supplier transaction")
            cursor.close()
            return ("Something went wrong while saving the entry.", 500)

        cursor.close()

        return redirect(f"/supplier_detail/{supplier_id}")

    cursor.execute("""
        SELECT supplier_id, name, amount
        FROM suppliers
        WHERE supplier_id = %s
    """, (supplier_id,))

    supplier = cursor.fetchone()

    if not supplier:
        cursor.close()
        return ("Supplier not found.", 404)

    cursor.execute("""
        SELECT *
        FROM supplier_transactions
        WHERE supplier_id = %s
        ORDER BY transaction_id ASC
    """, (supplier_id,))

    transactions = cursor.fetchall()

    cursor.close()

    return render_template("supplier_detail.html", supplier=supplier, transactions=transactions)


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    app.run(debug=True)