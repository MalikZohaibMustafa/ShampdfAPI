import os
from bidi.algorithm import get_display
import arabic_reshaper
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from reportlab.platypus import ListFlowable, ListItem

from reportlab.lib import colors
from reportlab.pdfgen import canvas
import zipfile

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import datetime
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.utils import ImageReader

from bidi.algorithm import get_display
import arabic_reshaper
from googletrans import Translator, LANGUAGES
from google.cloud import translate_v2 as translate

from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

amiri_regular_path = 'Amiri-Regular.ttf'
amiri_bold__path = 'Amiri-Bold.ttf'
amiri_italic_path= 'Amiri-Italic.ttf'
amiri_bold_italic_path = 'Amiri-BoldItalic.ttf'

pdfmetrics.registerFont(TTFont('Amiri', amiri_regular_path))
pdfmetrics.registerFont(TTFont('Amiri-Bold', amiri_bold__path))
pdfmetrics.registerFont(TTFont('Amiri-Italic', amiri_italic_path))
pdfmetrics.registerFont(TTFont('Amiri-BoldItalic', amiri_bold_italic_path))
page_width, page_height = letter
stamp_image_path = 'stamp.jpeg'
light_blue = colors.Color(0.7, 0.8, 0.9)  # Light blue for headers
darker_blue = colors.Color(0.6, 0.7, 0.8)  # Slightly darker blue for product names
skin_color = colors.Color(1, 0.894, 0.769)  # Skin color for specific cells
light_grey = colors.lightgrey

app = Flask(__name__)
CORS(app)
def has_discounts(productList):
    return any(float(product.get('discount', 0)) > 0 for product in productList)

def translate_text(text, dest_language):
    translator = Translator()
    translation = translator.translate(text, dest=dest_language)
    return translation.text

def reshape_arabic(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

@app.route('/generate-pdf/<int:quotation_id>/<language>', methods=['POST'])
def generate_pdf(quotation_id, language):
    if not quotation_id:
        return jsonify({"error": "Quotation not found"}), 404

    data = request.json
    
    if language == 'english':
        pdf_path = create_pdf(quotation_id, data, 'english')
    elif language == 'arabic':
        pdf_path = create_pdf(quotation_id, data, 'arabic')
    else:
        return jsonify({"error": "Invalid language"}), 400

    return send_file(pdf_path, as_attachment=True)


def create_pdf(quotation_id,data, language):
    current_year = datetime.datetime.now().year  # Get the current year

    if language == 'arabic':
        styles = getSampleStyleSheet()
        pdf_path = f"Arabic_quotation_{language}.pdf"
        paragraph_right_style = ParagraphStyle('ArabicStyle', fontName='Amiri', alignment=TA_RIGHT)
        paragraph_left_style = ParagraphStyle('ArabicStyle', fontName='Amiri', alignment=TA_LEFT)
        paragraph_center_style = ParagraphStyle('ArabicStyle', fontName='Amiri', alignment=TA_CENTER)
        arabic_bold_style_Right = ParagraphStyle(
            'ArabicBold',
            parent=styles['Normal'],
            fontName='Amiri-Bold',
            fontSize=12,  # Set the desired font size
            alignment=TA_RIGHT
        )
        arabic_bold_style_Left = ParagraphStyle(
            'ArabicBold',
            parent=styles['Normal'],
            fontName='Amiri-Bold',
            fontSize=12,  # Set the desired font size
            alignment=TA_LEFT
        )
        arabic_bold_style_Center = ParagraphStyle(
            'ArabicBold',
            parent=styles['Normal'],
            fontName='Amiri-Bold',
            fontSize=12,  # Set the desired font size
            alignment=TA_CENTER
        )
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        elements = []
        overall_total = 0
        tax=15
        background_image_path = 'bg.jpeg'  
        background_image = ImageReader(background_image_path)
        def create_page(canvas, doc):
                    canvas.drawImage(background_image, x=0, y=0, width=page_width, height=page_height)
                    canvas.saveState()
                    canvas.restoreState()
        doc.build(elements, onFirstPage=create_page, onLaterPages=create_page)

        elements.append(Spacer(1, 0.25*inch))
        styles = getSampleStyleSheet()
        bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold')

        elements.append(Image('CenterImage.PNG', 1.2*inch, 0.3*inch, hAlign=TA_CENTER))
        elements.append(Spacer(1, 0.25*inch))


        # Underline text in a Paragraph
        quote_text = reshape_arabic(f"عرض أسعار رقم العرض : {quotation_id} / {current_year}")
        underline_paragraph = Paragraph(f"<u>{quote_text}</u>", arabic_bold_style_Center)
        elements.append(underline_paragraph)
        elements.append(Spacer(1, 0.25*inch))


        
  # Underline date text
        date_text = data.get('quoteDate', '') + reshape_arabic(": تاريخ ")
        elements.append(Paragraph(f"<u>{date_text}</u>", paragraph_left_style))
        elements.append(Spacer(2, 0.25*inch))

        # Underline customer name text
        customer_name_text = data.get('customer', {}).get('name', '') + reshape_arabic(" عزيزي: ")
        elements.append(Paragraph(f"<u>{customer_name_text}</u>", arabic_bold_style_Right))
        elements.append(Spacer(2, 0.25*inch))


        elements.append(Paragraph(reshape_arabic(f"السالم عليكم ورحمة ٱللَّٰه وبركاته"),arabic_bold_style_Right))
        elements.append(Spacer(2, 0.25*inch))        
        elements.append(Paragraph(reshape_arabic(f"يسرنا أن نتقدم اليكم بعرض األسعار التالي :"),arabic_bold_style_Right))
        elements.append(Spacer(1, 0.25*inch))        
        customer_name = data.get('customer', {}).get('name', '')  # Extract customer name
        discount_present = has_discounts(data['productList'])
        arabic_customer_name = reshape_arabic(f"{current_year} {customer_name} اقتباس")

        

        if discount_present:
            arabic_table_headers = [
            reshape_arabic('السعر االجمالي \ ريال'), #Total Price/SAR
            reshape_arabic('العدد'), #Quantity
            reshape_arabic('السعر المخفض/ريال'), #Discounted Price/SAR
            reshape_arabic('السعر االفرادي \ ريال'), #Price/SAR
            reshape_arabic('القياس - سنوات'), #Size
            reshape_arabic('المرحلة') #Product Name 
        ]
        else:
            arabic_table_headers = [
            reshape_arabic('السعر االجمالي \ ريال'), #Total Price/SAR
            reshape_arabic('العدد'), #Quantity
            reshape_arabic('السعر االفرادي \ ريال'), #Price/SAR
            reshape_arabic('القياس - سنوات'), #Size
            reshape_arabic('المرحلة') #Product Name 
        ]
        table_data = [
            [arabic_customer_name],  # Use customer name and current year here
            arabic_table_headers
        ]
      
        
        for product in data['productList']:
            product_name = reshape_arabic(product['product']['arabicProductName'])
            base_price = float(product['product']['basePrice'])

            for size in product['selectedSizes']:
                base_price = float(product['product']['basePrice'])
                quantity = float(product['quantity'])
                individual_discount = float(product.get('discount', 0)) / 100

                discounted_price = base_price * (1 - individual_discount)
                total_price = discounted_price * quantity
                overall_total += total_price
                if discount_present:
                    row = [
                        "{:.2f}".format(total_price),
                        str(quantity),
                        "{:.2f}".format(discounted_price),
                        "{:.2f}".format(base_price),
                        size['size'],
                        product_name,
                    ]
                else:
                    row = [
                        "{:.2f}".format(total_price),
                        str(quantity),
                        "{:.2f}".format(base_price),
                        size['size'],
                        product_name,
                    ]
                table_data.append(row)
                 # Add an empty row after each product entry
                empty_row = [''] * len(row)  # Adjust the number of columns as needed
                table_data.append(empty_row)
                
                product_name = ""  # Clear pro

  
        tax_percent=15
        tax_amount = overall_total * (tax_percent / 100)
        grand_total = overall_total + tax_amount

        table_style = TableStyle([
            # Style for the top row
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('SPAN', (0, 0), (-1, 0)),
            ('FONTNAME', (0, 0), (-1, -4), 'Amiri-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0, colors.black),

            # Style for header row
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#d3e5f0")),
            ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, 1), 'Amiri-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 12),
        ])
      
       

        tax_percent = 15
        tax_amount = overall_total * (tax_percent / 100)
        grand_total = overall_total + tax_amount

        # Adjusting for RTL, these rows are added at the end
        subtotal_row = [f"{overall_total:.2f} SAR",reshape_arabic("المجموع الفرعي:"), "", "", ""]
        tax_row = [ f"{tax_amount:.2f} SAR", reshape_arabic(f"الضريبة ({tax_percent}%):"), "", "", ""]
        grand_total_row = [ f"{grand_total:.2f} SAR",reshape_arabic("الإجمالي النهائي:"), "", "", ""]

        # Append the total rows to table data
        table_data.extend([subtotal_row, tax_row, grand_total_row])

        n = len(table_data)
        for index, row in enumerate(table_data[2:], start=2):  # Skip header and title row
            if index > 1 and index < n - 3:  # Adjust indices as needed
                # Apply light blue background to product name cell
                # Assuming product names are in the last column for RTL layout
                table_style.add('BACKGROUND', (-1, index), (-1, index), colors.HexColor("#b2c4db"))

                # Check for empty row (separator) and apply light grey
                if row == [''] * len(row):
                    table_style.add('BACKGROUND', (0, index), (-1, index), colors.HexColor("#dee0e3"))
            elif index >= n - 3:
                # This is a subtotal, tax, or total row
                # Apply skin color background to these rows
                table_style.add('BACKGROUND', (0, 1), (-1, 0), skin_color)
                # Ensure the text in these rows is bold

        table_style.add('ALIGN', (0, 0), (-1, -1), 'CENTER')
        table_style.add('SPAN', (0, 0), (-1, 0))  # For the title ro
        # Total rows styling
        n = len(table_data)
        table_style.add('BACKGROUND', (0, n-1), (1, n-1), skin_color)
        table_style.add('FONTNAME', (0, n-3), (-1, n-1), 'Amiri-Bold')

     
        # Create the table with the updated data and style
        arabic_table = Table(table_data, style=table_style)
        elements.append(arabic_table)

        elements.append(Spacer(2, 0.25*inch))

        elements.append(Paragraph(reshape_arabic(f"مدة التسليم: 120 يوم عمل، تبدأ من الموافقة وتحويل السلفة"),arabic_bold_style_Right))
        elements.append(Spacer(2, 0.25*inch))

        elements.append(Paragraph(reshape_arabic(f"طريقة الدفع: 65% عند التأكيد و 35% عند التسليم. يجب تحويل المبلغ إلى حساب المنظمة."),arabic_bold_style_Right))
        elements.append(Spacer(2, 0.25*inch))
        elements.append(Paragraph(reshape_arabic(f"تفضلوا بقبول فائق االحترام"), arabic_bold_style_Right))
        elements.append(Spacer(2, 0.25*inch))
        elements.append(Paragraph(reshape_arabic(f"زي الشام للأناقة"), arabic_bold_style_Right))
        elements.append(Spacer(2, 0.25*inch))
        elements.append(Image(stamp_image_path, 1.25*inch, 1.25*inch, hAlign='RIGHT'))  # Align the image as needed


        doc.build(elements)
    
        return pdf_path

    else:
        pdf_path = f"quotation_{language}.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        elements = []
        overall_total = 0
        tax_percent=15
        background_image_path = 'bg.jpeg'
        background_image = ImageReader(background_image_path)

        def create_page(canvas, doc):
            canvas.drawImage(background_image, x=0, y=0, width=page_width, height=page_height)
            canvas.saveState()
            canvas.restoreState()
            
        doc.build(elements, onFirstPage=create_page, onLaterPages=create_page)

        elements.append(Spacer(3, 0.5*inch))
        
        elements.append(Image('CenterImage.PNG', 1.2*inch, 0.3*inch, hAlign=TA_CENTER))
        elements.append(Spacer(1, 0.25*inch))

        styles = getSampleStyleSheet()
        bold_center_style = ParagraphStyle('BoldCenterStyle', parent=styles['Normal'], fontName='Helvetica-Bold', alignment=TA_CENTER)
        bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold')

# Underline text in a Paragraph
        quotation_number_text = f"Quotation number: {quotation_id} / {current_year}"
        underline_quotation_number_paragraph = Paragraph(f"<u>{quotation_number_text}</u>", bold_center_style)
        elements.append(underline_quotation_number_paragraph)
        elements.append(Spacer(1, 0.25*inch))

        elements.append(Paragraph("Date: " + data.get('quoteDate', '') , bold_style))
        elements.append(Paragraph("Dear: " + data['customer']['name'], bold_style))
        elements.append(Paragraph("We are glad to present you with the following quotation:", bold_style))
        elements.append(Spacer(1, 0.25*inch))

    # Styles
        styles = getSampleStyleSheet()
        bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold')
        customer_name = data.get('customer', {}).get('name', '')
        discount_present = has_discounts(data['productList'])

        if discount_present:
            table_headers = ["Product Name", "Size", "Price/SAR", "Discounted Price/SAR", "Quantity", "Net Amount/SAR"]
        else:
            table_headers = ["Product Name", "Size", "Price/SAR", "Quantity", "Net Amount/SAR"]

        table_data = [
            [f"{customer_name} Quotation {current_year}"],  # Use customer name and current year here
            table_headers
        ]
       
        # Populate table_data with items from data['productList']
        for product in data['productList']:
            product_name = product['product']['productName']
            base_price = float(product['product']['basePrice'])

            for size in product['selectedSizes']:
                base_price = float(product['product']['basePrice'])
                quantity = float(product['quantity'])
                individual_discount = float(product.get('discount', 0)) / 100

                discounted_price = base_price * (1 - individual_discount)
                total_price = discounted_price * quantity
                overall_total += total_price

                if discount_present:
                    row = [
                        product_name,
                        size['size'],
                        "{:.2f}".format(base_price),
                        "{:.2f}".format(discounted_price) if individual_discount > 0 else "-",
                        str(quantity),
                        "{:.2f}".format(total_price)
                    ]
                else:
                    row = [
                        product_name,
                        size['size'],
                        "{:.2f}".format(base_price),
                        str(quantity),
                        "{:.2f}".format(total_price)
                    ]
                table_data.append(row)
                
                # Add an empty row after each product entry
                empty_row = [''] * len(row)  # Adjust the number of columns as needed
                table_data.append(empty_row)
                
                product_name = ""  # Clear product name for the next iteration

        
        table_style = TableStyle([
            # Top row style
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('SPAN', (0, 0), (-1, 0)),  # if you have a title row that spans across columns
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            # Header row style
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#d3e5f0")),  # Apply the lighter blue color here
            ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 10),
            # Other styles
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 2), (-1, -1), 'CENTER'),
            # Add more styles as needed
        ])
        for index in range(3, len(table_data), 2):  # Start from the first empty row and skip every other row
            table_style.add('BACKGROUND', (0, index), (-1, index), colors.HexColor("#dee0e3"))

        tax_amount = overall_total * (tax_percent / 100)
        grand_total = overall_total + tax_amount

        column_offset = 0 if discount_present else 1  # Adjust index if no discount column
        table_data.append([""] * (4 - column_offset) + ["Subtotal (SAR):", f"{overall_total:.2f}"])
        table_data.append([""] * (4 - column_offset) + [f"15% Tax (SAR):", f"{tax_amount:.2f}"])
        table_data.append([""] * (4 - column_offset) + ["Grand Total (SAR):", f"{grand_total:.2f}"])

        n = len(table_data)  # Total number of rows after appending totals
        m = len(table_headers)  # Total number of columns based on headers
        table_style.add('BACKGROUND', (m-2, n-3), (m-1, n-1), skin_color)  # Adjust for subtotal, tax, grand total rows
        table_style.add('FONTNAME', (m-2, n-3), (m-1, n-1), 'Helvetica-Bold')  # Make text bold for totals

        n = len(table_data)


      
        # Assuming product names are in the first column after header
        for row_index in range(2, n-3, 2):  # Adjust the range to skip header and empty rows
            table_style.add('FONTNAME', (0, row_index), (0, row_index), 'Helvetica-Bold')
            table_style.add('BACKGROUND', (0, row_index), (0, row_index+1), colors.HexColor("#b2c4db"))


        for row_index in range(2, n-3, 2):  # Adjust the range to target the newly added empty rows
                    table_style.add('BACKGROUND', (0, row_index+1), (-1, row_index+1), colors.HexColor("#dee0e3"))


        table_style.add('FONTNAME', (4, n-3), (4, n-2), 'Helvetica-Bold')  # Apply bold only to headings
        table_style.add('TEXTCOLOR', (4, n-3), (4, n-2), colors.black)  # Ensure text color is black for visibility
        table_style.add('FONTSIZE', (4, n-3), (4, n-2), 10)  # Adjust font size as needed

        # Make the entire last row bold
        table_style.add('FONTNAME', (0, n-1), (-1, n-1), 'Helvetica-Bold')  # Apply bold to the entire last row
        table_style.add('TEXTCOLOR', (0, n-1), (-1, n-1), colors.black)  # Ensure text color is black for visibility
        table_style.add('FONTSIZE', (0, n-1), (-1, n-1), 10)  # Adjust font size as needed

        table = Table(table_data, colWidths=[None] * 1, style=table_style)
        elements.append(table)
       
    
    # Styles
        styles = getSampleStyleSheet()
        bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold')

        bullet_points = [
            ("Delivery period:", " 120 days starting from the commissioning and the advance payment transfer."),
            ("Payment method:", " 65% upon commissioning and 35% upon delivery. The amount will be transferred to the company's account."),
        ]
        # Create a ListFlowable object with ListItem objects
        bullet_list = ListFlowable(
            [create_bullet_point(bp[0] + bp[1], len(bp[0]), styles['Normal'], bold_style) for bp in bullet_points],
            bulletType='bullet',
            start='bulletchar',
            leftIndent=35,
        )
        # Adding paragraphs in bold
        elements.append(Spacer(0.5, 0.25*inch))
        elements.append(Paragraph("We hope that our proposal exceeds your expectations, and we look forward to working with you.", bold_style))
                # Add the bullet list to the elements
        elements.append(bullet_list)
        elements.append(Paragraph("Please accept my highest respect.", bold_style))
        elements.append(Spacer(0.25, 0.25*inch))
        elements.append(Paragraph("Sham Elegance Uniform", bold_style))
        elements.append(Image(stamp_image_path, 1.25*inch, 1.25*inch, hAlign='LEFT'))  # Align the image as needed

        # elements.append(Paragraph("Sham Elegance Uniform", bold_style))
     
        if language == 'arabic':
            new_elements = []
            for element in elements:
                if isinstance(element, Paragraph):
                    # Apply reshaping and bidi reordering to Arabic text
                    arabic_text = reshape_arabic(element.text)
                    new_paragraph = Paragraph(arabic_text, element.style)
                    new_elements.append(new_paragraph)
                else:
                    new_elements.append(element)
            elements = new_elements


        # Generate PDF
        doc.build(elements)
    
        return pdf_path

def reshape_arabic(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def create_bullet_point(text, bold_part_end_index, normal_style, bold_style):
    """
    Creates a bullet point with a bold part before the colon and a normal part after.
    
    :param text: The text of the bullet point.
    :param bold_part_end_index: The index where the bold part ends and the normal part begins.
    :param normal_style: The style to be applied to the normal part.
    :param bold_style: The style to be applied to the bold part.
    :return: A ListItem containing the styled bullet point.
    """
    bold_part = text[:bold_part_end_index]
    normal_part = text[bold_part_end_index:]
    
    # Combine the bold and normal parts into one paragraph
    bullet_text = f'<b>{bold_part}</b>{normal_part}'
    return ListItem(Paragraph(bullet_text, normal_style))

if __name__ == '__main__':
    app.run(debug=True)

