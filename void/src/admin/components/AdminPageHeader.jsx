const AdminPageHeader = ({ title, description, action, meta }) => (
  <header className="admin-page-header">
    <div className="min-w-0">
      <p className="admin-eyebrow">Project VOID / Admin</p>
      <h2>{title}</h2>
      {description && <p className="admin-page-description">{description}</p>}
    </div>
    {(action || meta) && <div className="admin-page-header-aside">{action || meta}</div>}
  </header>
);

export default AdminPageHeader;
