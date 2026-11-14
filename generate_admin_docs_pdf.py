"""
Script to generate the comprehensive VOID E-Commerce Admin Migration & Integration PDF.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

PDF_OUTPUT_PATH = r"D:\project\VOID_Admin_Panel_Migration_Documentation.pdf"


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic total page count."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(40, A4[1] - 30, "VOID E-Commerce — Complete Admin Panel DRF Migration & Integration")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(40, A4[1] - 34, A4[0] - 40, A4[1] - 34)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, 36, A4[0] - 40, 36)
        
        self.drawString(40, 24, "CONFIDENTIAL & PROPRIETARY — VOIDCORP ARCHITECTURE")
        self.drawRightString(A4[0] - 40, 24, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        PDF_OUTPUT_PATH,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=14
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12.5,
        leading=16,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#f8fafc'),
        spaceAfter=0
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor('#1e293b')
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#0f172a')
    )

    story = []

    # Title Banner
    story.append(Paragraph("VOID E-COMMERCE — ADMIN PANEL MIGRATION", title_style))
    story.append(Paragraph("TECHNICAL DOCUMENTATION: REACT ADMIN TO DJANGO REST FRAMEWORK INTEGRATION", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f172a'), spaceAfter=10))

    # Meta Info Card
    meta_data = [
        [
            Paragraph("<b>Project:</b> VOID E-Commerce", table_cell),
            Paragraph("<b>Target Stack:</b> React 19 + Django REST Framework", table_cell),
            Paragraph("<b>Test Suite:</b> 44/44 Passed (100%)", table_cell)
        ],
        [
            Paragraph("<b>Migration:</b> json-server (db.json) &rarr; DRF", table_cell),
            Paragraph("<b>Auth:</b> JWT (In-Memory) + HttpOnly Cookies", table_cell),
            Paragraph("<b>Build Status:</b> Vite 1775 Modules (0 Errors)", table_cell)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[170, 185, 165])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # 1. Executive Summary
    story.append(Paragraph("1. Executive Summary & Migration Objective", h1_style))
    story.append(Paragraph(
        "The VOID Admin Panel originally communicated with a mock JSON-Server (<code>db.json</code>) operating on port 5000. "
        "This legacy architecture lacked database consistency, security permissions, transactional safety, and production resilience. "
        "The migration goal was to connect the established React Admin Panel to the production Django REST Framework backend while strictly "
        "preserving the dark cyberpunk aesthetic, UI component structure, and responsive layout.",
        body_style
    ))

    # 2. Complete Inventory of New & Modified Files
    story.append(Paragraph("2. Inventory of New Files & Modifications", h1_style))
    
    file_table_data = [
        [Paragraph("File Path", table_header), Paragraph("Type", table_header), Paragraph("Key Role & Responsibility", table_header)],
        
        [Paragraph("<code>apps/accounts/permissions.py</code>", table_cell),
         Paragraph("<font color='#16a34a'><b>NEW</b></font>", table_cell),
         Paragraph("Implements <code>IsAdminUserOrStaff</code> to enforce that requestors are authenticated with <code>is_staff=True</code> or <code>is_superuser=True</code>.", table_cell)],

        [Paragraph("<code>apps/orders/admin_views.py</code>", table_cell),
         Paragraph("<font color='#16a34a'><b>NEW</b></font>", table_cell),
         Paragraph("Provides <code>AdminOrderListView</code> and <code>AdminOrderDetailView</code> for listing and status management (Pending, Deployed, Delivered, Cancelled).", table_cell)],

        [Paragraph("<code>apps/accounts/admin_views.py</code>", table_cell),
         Paragraph("<font color='#16a34a'><b>NEW</b></font>", table_cell),
         Paragraph("Provides <code>AdminUserListView</code> and <code>AdminUserDetailView</code> with suspension toggling (<code>is_active</code>) and self-lockout prevention.", table_cell)],

        [Paragraph("<code>apps/orders/dashboard_views.py</code>", table_cell),
         Paragraph("<font color='#16a34a'><b>NEW</b></font>", table_cell),
         Paragraph("Provides <code>AdminDashboardView</code> aggregating total users, revenue, inventory status, 30-day timeline chart, and top-selling variants in INR.", table_cell)],

        [Paragraph("<code>apps/accounts/serializers.py</code>", table_cell),
         Paragraph("<font color='#2563eb'><b>MODIFIED</b></font>", table_cell),
         Paragraph("Updated <code>UserProfileSerializer</code> to inject <code>role</code> ('admin'/'customer'), <code>status</code> ('Active'/'Banned'), and formatted <code>name</code>.", table_cell)],

        [Paragraph("<code>apps/catalog/serializer.py</code>", table_cell),
         Paragraph("<font color='#2563eb'><b>MODIFIED</b></font>", table_cell),
         Paragraph("Added <code>Base64ImageField</code> and <code>AdminProductWriteSerializer</code> with auto category creation and nested ingredient transactions.", table_cell)],

        [Paragraph("<code>apps/catalog/views.py</code>", table_cell),
         Paragraph("<font color='#2563eb'><b>MODIFIED</b></font>", table_cell),
         Paragraph("Enforces admin permissions on create/update/delete; blocks decommissioning products referenced by completed customer orders.", table_cell)],

        [Paragraph("<code>apps/orders/urls.py</code>", table_cell),
         Paragraph("<font color='#2563eb'><b>MODIFIED</b></font>", table_cell),
         Paragraph("Registered <code>admin/</code>, <code>admin/&lt;uuid&gt;/</code>, and <code>admin/dashboard/</code> routes under <code>/api/v1/orders/</code>.", table_cell)],

        [Paragraph("<code>apps/accounts/urls.py</code>", table_cell),
         Paragraph("<font color='#2563eb'><b>MODIFIED</b></font>", table_cell),
         Paragraph("Registered <code>admin/users/</code> and <code>admin/users/&lt;id&gt;/</code> routes under <code>/api/v1/accounts/</code>.", table_cell)],

        [Paragraph("<code>src/api/apiClient.js</code>", table_cell),
         Paragraph("<font color='#2563eb'><b>MODIFIED</b></font>", table_cell),
         Paragraph("Removed legacy JSON server (localhost:5000); routed admin calls via <code>catalogClient</code>, <code>ordersClient</code>, and <code>accountsClient</code> with JWT interceptors.", table_cell)],

        [Paragraph("<code>src/admin/pages/*.jsx</code>", table_cell),
         Paragraph("<font color='#2563eb'><b>MODIFIED</b></font>", table_cell),
         Paragraph("Rewrote <code>InventoryManager</code>, <code>OrderManifest</code>, <code>UserDirectory</code>, and <code>AdminDashboard</code> to map DRF schemas and TanStack queries.", table_cell)],
    ]
    
    t_files = Table(file_table_data, colWidths=[150, 60, 310])
    t_files.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_files)

    story.append(PageBreak())

    # 3. System Architecture & Workflows
    story.append(Paragraph("3. System Architecture & Workflows", h1_style))
    
    story.append(Paragraph("3.1 Security & Authentication Workflow", h2_style))
    story.append(Paragraph(
        "Authentication is architected to guarantee zero token leakage while providing seamless user session management:",
        body_style
    ))
    story.append(Paragraph("&bull; <b>In-Memory Token Storage:</b> Access tokens are stored strictly in JS memory (never in localStorage or sessionStorage to prevent XSS exfiltration).", bullet_style))
    story.append(Paragraph("&bull; <b>HttpOnly Cookies:</b> Refresh tokens reside in browser cookies with <code>HttpOnly; SameSite=Lax; Secure</code> flags.", bullet_style))
    story.append(Paragraph("&bull; <b>Client-Side Clearance (AdminRoute):</b> On mount, <code>restoreSession()</code> hits <code>/token/refresh/</code> and fetches <code>/profile/</code>. <code>AdminRoute</code> checks <code>user.role === 'admin'</code> (derived from Django's <code>is_staff/is_superuser</code>).", bullet_style))
    story.append(Paragraph("&bull; <b>Server-Side Enforcement (DRF):</b> Every admin endpoint enforces <code>IsAdminUserOrStaff</code>. Unauthenticated requests receive HTTP 401; non-admin users receive HTTP 403.", bullet_style))
    story.append(Paragraph("&bull; <b>Single Refresh Promise Collapsing:</b> If multiple parallel calls encounter an expired access token, the interceptor queues subsequent requests and executes only one refresh call to avoid race conditions.", bullet_style))

    # Architecture diagram block
    diag_code = (
        "+-------------------------------------------------------------------------+\n"
        "|                         REACT FRONTEND CLIENT                           |\n"
        "|  AdminRoute.jsx  -->  catalogClient / ordersClient / accountsClient     |\n"
        "+------------------------------------+------------------------------------+\n"
        "                                     |  HTTP Requests (Bearer Access Token)\n"
        "                                     v\n"
        "+------------------------------------+------------------------------------+\n"
        "|                   DJANGO REST FRAMEWORK BACKEND                         |\n"
        "|                                                                         |\n"
        "|  1. CookieTokenRefreshView  -->  Issues fresh in-memory JWT Access Token|\n"
        "|  2. UserProfileSerializer   -->  Exposes role ('admin'/'customer')      |\n"
        "|  3. IsAdminUserOrStaff      -->  Validates is_staff / is_superuser      |\n"
        "|  4. Admin Order Views       -->  Fulfillment status dispatch & details  |\n"
        "|  5. Admin Catalog Views     -->  Product CRUD + Safe decommission check |\n"
        "|  6. Admin User Views        -->  Directory + Suspension + Self-lockout  |\n"
        "|  7. Admin Dashboard View    -->  Aggregated analytics & TruncDate stats |\n"
        "+------------------------------------+------------------------------------+\n"
        "                                     |  Django ORM Queries\n"
        "                                     v\n"
        "+------------------------------------+------------------------------------+\n"
        "|                  DATABASE LAYER (PostgreSQL / SQLite)                   |\n"
        "+-------------------------------------------------------------------------+"
    )
    t_diag = Table([[Paragraph(f"<pre>{diag_code}</pre>", code_style)]], colWidths=[520])
    t_diag.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#0f172a')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#334155')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_diag)
    story.append(Spacer(1, 10))

    # 4. Detailed Working of Each Function & Component
    story.append(Paragraph("4. Detailed Working of Each Function & Component", h1_style))

    story.append(Paragraph("4.1 Permission Enforcement: <code>IsAdminUserOrStaff</code>", h2_style))
    story.append(Paragraph(
        "<b>File:</b> <code>apps/accounts/permissions.py</code><br/>"
        "<b>Function:</b> <code>has_permission(self, request, view)</code><br/>"
        "<b>Working:</b> Inspects <code>request.user</code> to confirm <code>is_authenticated</code> is True and that either <code>is_staff</code> or <code>is_superuser</code> is set. Returns boolean True to proceed or False, triggering DRF's automatic <code>HTTP 403 Forbidden</code> response.",
        body_style
    ))

    story.append(Paragraph("4.2 Profile Serializer Identity Bridge", h2_style))
    story.append(Paragraph(
        "<b>File:</b> <code>apps/accounts/serializers.py</code><br/>"
        "<b>Class:</b> <code>UserProfileSerializer</code><br/>"
        "<b>Methods:</b><br/>"
        "&bull; <code>get_role(obj)</code>: Evaluates <code>'admin' if (obj.is_staff or obj.is_superuser) else 'customer'</code>.<br/>"
        "&bull; <code>get_status(obj)</code>: Returns <code>'Active' if obj.is_active else 'Banned'</code>.<br/>"
        "&bull; <code>get_name(obj)</code>: Formats <code>f'{obj.first_name} {obj.last_name}'</code> or defaults to email prefix.",
        body_style
    ))

    story.append(Paragraph("4.3 Catalog & Product Management Implementation", h2_style))
    story.append(Paragraph(
        "<b>Files:</b> <code>apps/catalog/serializer.py</code> & <code>apps/catalog/views.py</code><br/>"
        "<b>Components & Logic:</b><br/>"
        "&bull; <code>Base64ImageField.to_internal_value()</code>: Decodes base64 data-URIs sent from the React dropzone into Django <code>ContentFile</code> binary assets.<br/>"
        "&bull; <code>AdminProductWriteSerializer.validate_series()</code>: Normalizes series tokens (maps <code>'ZERO'</code> to <code>'VOID'</code>, checks valid choices).<br/>"
        "&bull; <code>AdminProductWriteSerializer.validate_category()</code>: Automatically executes <code>Category.objects.get_or_create(name=value.strip())</code>.<br/>"
        "&bull; <code>AdminProductWriteSerializer.create() / update()</code>: Atomic transaction that creates the product and synchronizes nested ingredients.<br/>"
        "&bull; <code>ProductDetailsAPI.destroy()</code>: Checks <code>instance.order_items.exists()</code>. If true, rejects deletion with HTTP 400 ('Cannot decommission variant referenced by existing orders'), protecting order history.",
        body_style
    ))

    story.append(PageBreak())

    story.append(Paragraph("4.4 Order Administration & Manifest Dispatch", h2_style))
    story.append(Paragraph(
        "<b>File:</b> <code>apps/orders/admin_views.py</code><br/>"
        "<b>Components & Logic:</b><br/>"
        "&bull; <code>AdminOrderStatusSerializer.validate_status()</code>: Case-insensitively maps incoming frontend status labels ('Pending', 'Deployed', 'Delivered', 'Cancelled') to Django model Status choices (<code>PLACED</code>, <code>SHIPPED</code>, <code>DELIVERED</code>, <code>CANCELLED</code>).<br/>"
        "&bull; <code>AdminOrderListView.get_queryset()</code>: Performs <code>Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')</code> to guarantee single-query performance.<br/>"
        "&bull; <code>AdminOrderDetailView.patch()</code>: Applies status transitions via <code>update_fields=['status', 'updated_at']</code> and logs the administrative action.",
        body_style
    ))

    story.append(Paragraph("4.5 User Clearance & Account Directory", h2_style))
    story.append(Paragraph(
        "<b>File:</b> <code>apps/accounts/admin_views.py</code><br/>"
        "<b>Components & Logic:</b><br/>"
        "&bull; <code>AdminUserReadSerializer.get_order_count()</code>: Injects customer order count directly into user cards.<br/>"
        "&bull; <code>AdminUserDetailView.patch()</code>: Updates <code>is_active</code> (suspend/restore) and <code>is_staff</code> (clearance promotion).<br/>"
        "&bull; <b>Self-Lockout Safeguard:</b> If <code>user.pk == request.user.pk</code>, rejects mutation with HTTP 403 ('You cannot modify your own account through the admin panel').",
        body_style
    ))

    story.append(Paragraph("4.6 Dashboard Analytics Engine", h2_style))
    story.append(Paragraph(
        "<b>File:</b> <code>apps/orders/dashboard_views.py</code><br/>"
        "<b>Component:</b> <code>AdminDashboardView.get()</code><br/>"
        "<b>Telemetry Calculations:</b><br/>"
        "&bull; <code>User.objects.aggregate()</code>: Total users and active accounts.<br/>"
        "&bull; <code>Product.objects.aggregate()</code>: Total inventory units, low stock count (&le; 10 units), out of stock count.<br/>"
        "&bull; <code>Order.objects.aggregate()</code>: Total orders, active dispatches, and gross revenue sum (filtered strictly to <code>payment_status=PAID</code>).<br/>"
        "&bull; <code>TruncDate('created_at')</code>: Portable 30-day timeline revenue calculation compatible with PostgreSQL and SQLite.<br/>"
        "&bull; <code>OrderItem.objects.filter(...)</code>: Identifies top-selling product variants by quantity and calculates revenue contribution.",
        body_style
    ))

    # 5. Frontend Admin Pages Deep Dive
    story.append(Paragraph("5. Frontend Admin Pages Integration", h1_style))
    
    ui_table_data = [
        [Paragraph("Admin Page", table_header), Paragraph("Client & API Endpoint", table_header), Paragraph("Key Features & Logic Handled", table_header)],
        
        [Paragraph("<b>InventoryManager.jsx</b>", table_cell),
         Paragraph("<code>catalogClient</code><br/><code>/api/v1/catalog/products/</code>", table_cell),
         Paragraph("&bull; Real-time search by variant name or UID.<br/>"
                   "&bull; Series filtration (FLOW, VOID, RITE, FORM) and stock levels.<br/>"
                   "&bull; Add/Edit modal supporting base64 image dropzone.<br/>"
                   "&bull; Safe decommission alert displaying backend error toasts.", table_cell)],

        [Paragraph("<b>OrderManifest.jsx</b>", table_cell),
         Paragraph("<code>ordersClient</code><br/><code>/api/v1/orders/admin/</code>", table_cell),
         Paragraph("&bull; Lists all customer transactions ordered newest-first.<br/>"
                   "&bull; Search by UUID, customer name, or customer email.<br/>"
                   "&bull; Filter by status (Pending, Deployed, Delivered, Cancelled) and time range.<br/>"
                   "&bull; Full manifest modal showing address, phone, and line items.", table_cell)],

        [Paragraph("<b>UserDirectory.jsx</b>", table_cell),
         Paragraph("<code>accountsClient</code> + <code>ordersClient</code><br/><code>/api/v1/accounts/admin/users/</code>", table_cell),
         Paragraph("&bull; Directory table with order fulfillment counts.<br/>"
                   "&bull; Customer Intelligence modal (LTV in INR, avg order value, top series).<br/>"
                   "&bull; Suspend / Restore account action with self-admin lock protection.", table_cell)],

        [Paragraph("<b>AdminDashboard.jsx</b>", table_cell),
         Paragraph("<code>ordersClient</code><br/><code>/api/v1/orders/admin/dashboard/</code>", table_cell),
         Paragraph("&bull; Single unified API call replacing client-side aggregation.<br/>"
                   "&bull; SVG AreaChart for 30-day transaction performance.<br/>"
                   "&bull; BarChart for individual payment streams.<br/>"
                   "&bull; Top Sellers card grid with product preview images.", table_cell)],
    ]
    t_ui = Table(ui_table_data, colWidths=[120, 140, 260])
    t_ui.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_ui)

    story.append(PageBreak())

    # 6. Verification and Test Results
    story.append(Paragraph("6. Verification & Automated Test Results", h1_style))
    story.append(Paragraph(
        "A comprehensive automated test suite (<code>apps/accounts/tests.py</code>) was written and executed to ensure "
        "complete system integrity, zero regressions, and strict security enforcement across all integrated layers.",
        body_style
    ))

    test_summary_data = [
        [Paragraph("Test Suite Module", table_header), Paragraph("Count", table_header), Paragraph("Scope of Verification", table_header), Paragraph("Result", table_header)],
        
        [Paragraph("Permission Tests", table_cell), Paragraph("4", table_cell),
         Paragraph("Blocks unauthenticated and customer users; permits staff & superusers.", table_cell),
         Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell)],

        [Paragraph("UserProfileSerializer Tests", table_cell), Paragraph("4", table_cell),
         Paragraph("Validates computed 'role', 'status', and 'name' fields across user types.", table_cell),
         Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell)],

        [Paragraph("Catalog Public & Admin Tests", table_cell), Paragraph("8", table_cell),
         Paragraph("Public read operations; admin create/update; blocks delete when order exists.", table_cell),
         Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell)],

        [Paragraph("Order Admin Tests", table_cell), Paragraph("9", table_cell),
         Paragraph("List all orders; order detail; status mutations; blocks customer writes.", table_cell),
         Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell)],

        [Paragraph("User Admin Tests", table_cell), Paragraph("10", table_cell),
         Paragraph("User listing; detail inspection; suspend/reactivate; prevents self-demotion.", table_cell),
         Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell)],

        [Paragraph("Dashboard Telemetry Tests", table_cell), Paragraph("6", table_cell),
         Paragraph("Confirms all required analytics keys, calculations, and seller rankings.", table_cell),
         Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell)],

        [Paragraph("Customer Regression Tests", table_cell), Paragraph("3", table_cell),
         Paragraph("Ensures customer-facing order endpoints isolate user data correctly.", table_cell),
         Paragraph("<font color='#16a34a'><b>PASSED</b></font>", table_cell)],
    ]
    t_test = Table(test_summary_data, colWidths=[140, 45, 275, 60])
    t_test.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_test)
    story.append(Spacer(1, 10))

    # Test Output Log Block
    log_text = (
        "Found 44 test(s).\n"
        "Applying migrations... OK\n"
        "----------------------------------------------------------------------\n"
        "Ran 44 tests in 17.937s\n\n"
        "OK\n"
        "Frontend Vite Build: 1775 modules transformed in 15.29s (0 errors)"
    )
    t_log = Table([[Paragraph(f"<pre>{log_text}</pre>", code_style)]], colWidths=[520])
    t_log.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#0f172a')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#334155')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_log)
    story.append(Spacer(1, 12))

    # 7. Environment Configuration Guide
    story.append(Paragraph("7. Environment Configuration Guide", h1_style))
    story.append(Paragraph(
        "To run the integrated application locally or in production, ensure the frontend environment variables in <code>void/.env.local</code> point to the corresponding Django REST endpoints:",
        body_style
    ))
    
    env_code = (
        "VITE_CATALOG_API_URL=http://localhost:8000/api/v1/catalog\n"
        "VITE_ACCOUNTS_API_URL=http://localhost:8000/api/v1/accounts\n"
        "VITE_ORDERS_API_URL=http://localhost:8000/api/v1/orders\n"
        "VITE_CART_API_URL=http://localhost:8000/api/v1/cart"
    )
    t_env = Table([[Paragraph(f"<pre>{env_code}</pre>", code_style)]], colWidths=[520])
    t_env.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#0f172a')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#334155')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_env)

    doc.build(story, canvasmaker=NumberedCanvas)
    print("PDF build complete:", PDF_OUTPUT_PATH)


if __name__ == "__main__":
    build_pdf()

