import { useEffect, useState } from "react";
import api, { apiErrorMessage } from "../api/axios.js";
import { useNotification } from "../context/NotificationContext.jsx";
import DataTable from "../components/DataTable.jsx";
import Pagination from "../components/Pagination.jsx";
import { Badge, ConfirmDialog } from "../components/Common.jsx";
import Modal from "../components/Modal.jsx";
import { useAuth } from "../context/AuthContext.jsx";

const ROLES = ["Admin", "Manager", "Member"];

export default function TeamManagement() {
  const { notify } = useNotification();
  const { user: currentUser } = useAuth();

  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 10 });
  const [loading, setLoading] = useState(true);
  const [roleFilter, setRoleFilter] = useState("");
  const [showAddUser, setShowAddUser] = useState(false);
  const [viewUser, setViewUser] = useState(null);
  const [manageUser, setManageUser] = useState(null);
  const [removeTarget, setRemoveTarget] = useState(null);

  const fetchUsers = async (page = 1) => {
    setLoading(true);
    try {
      const res = await api.get("/team/users", { params: { role: roleFilter || undefined, page, page_size: 10 } });
      setData(res.data);
    } catch (err) {
      notify(apiErrorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roleFilter]);

  const columns = [
    { key: "name", label: "Name", render: (u) => <span className="font-medium text-gray-800">{u.name}</span> },
    {
      key: "contact",
      label: "Contact Info",
      render: (u) => (
        <div>
          <p>{u.email}</p>
          <p className="text-xs text-gray-400">{u.phone || "-"}</p>
        </div>
      ),
    },
    { key: "status", label: "Status", render: (u) => <Badge label={u.status} /> },
    { key: "role", label: "Role" },
    {
      key: "actions",
      label: "Actions",
      render: (u) => (
        <div className="flex items-center gap-2">
          <button className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium px-3 py-1.5 rounded-md" onClick={() => setViewUser(u)}>
            View
          </button>
          <button className="btn-primary text-xs px-3 py-1.5" onClick={() => setManageUser(u)}>
            Manage
          </button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="card p-0 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 border-b border-gray-100">
          <h1 className="text-lg font-bold text-gray-900">Manage Users</h1>
          <div className="flex items-center gap-3">
            <select className="input-field w-44" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
              <option value="">Filter by Role</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <button className="btn-secondary text-sm" onClick={() => fetchUsers(data.page)}>
              ↻ Refresh
            </button>
            <button className="btn-primary text-sm" onClick={() => setShowAddUser(true)}>
              + Add User
            </button>
          </div>
        </div>

        <DataTable columns={columns} rows={data.items} loading={loading} emptyMessage="No users found." />
        <Pagination page={data.page} pageSize={data.page_size} total={data.total} onPageChange={(p) => fetchUsers(p)} />
      </div>

      {showAddUser && (
        <AddUserModal
          onClose={() => setShowAddUser(false)}
          onCreated={() => {
            setShowAddUser(false);
            fetchUsers(data.page);
          }}
        />
      )}

      {viewUser && (
        <Modal title="User Details" onClose={() => setViewUser(null)}>
          <div className="space-y-3 text-sm">
            <Row label="Name" value={viewUser.name} />
            <Row label="Email" value={viewUser.email} />
            <Row label="Phone" value={viewUser.phone || "-"} />
            <Row label="Role" value={viewUser.role} />
            <Row label="Status" value={viewUser.status} />
            <Row label="Joined" value={new Date(viewUser.created_at).toLocaleDateString("en-IN")} />
          </div>
        </Modal>
      )}

      {manageUser && (
        <ManageUserModal
          user={manageUser}
          currentUserId={currentUser?.id}
          onClose={() => setManageUser(null)}
          onSaved={() => {
            setManageUser(null);
            fetchUsers(data.page);
          }}
          onRequestRemove={(u) => {
            setManageUser(null);
            setRemoveTarget(u);
          }}
        />
      )}

      {removeTarget && (
        <ConfirmDialog
          title="Remove User"
          message={`Are you sure you want to remove "${removeTarget.name}" from the team?`}
          confirmLabel="Remove"
          danger
          onCancel={() => setRemoveTarget(null)}
          onConfirm={async () => {
            try {
              await api.delete(`/team/users/${removeTarget.id}`);
              notify("User removed");
              setRemoveTarget(null);
              fetchUsers(data.page);
            } catch (err) {
              notify(apiErrorMessage(err), "error");
            }
          }}
        />
      )}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between border-b border-gray-100 pb-2">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-800">{value}</span>
    </div>
  );
}

function AddUserModal({ onClose, onCreated }) {
  const { notify } = useNotification();
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "", role: "Member" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post("/team/users", form);
      notify("User added successfully");
      onCreated();
    } catch (err) {
      setError(apiErrorMessage(err, "Could not add user"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="Add User" onClose={onClose}>
      {error && <div className="mb-4 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-2">{error}</div>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
          <input required className="input-field" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input required type="email" className="input-field" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
          <input className="input-field" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Temporary Password</label>
          <input required minLength={6} type="password" className="input-field" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
          <select className="input-field" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? "Adding..." : "Add User"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ManageUserModal({ user, currentUserId, onClose, onSaved, onRequestRemove }) {
  const { notify } = useNotification();
  const [role, setRole] = useState(user.role);
  const [status, setStatus] = useState(user.status);
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    setLoading(true);
    try {
      await api.put(`/team/users/${user.id}`, { role, status });
      notify("User updated");
      onSaved();
    } catch (err) {
      notify(apiErrorMessage(err), "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title={`Manage ${user.name}`} onClose={onClose}>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
          <select className="input-field" value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
          <select className="input-field" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
          </select>
        </div>

        <div className="flex justify-between items-center pt-4 border-t border-gray-100">
          {user.id !== currentUserId ? (
            <button className="text-red-500 hover:text-red-700 text-sm font-medium" onClick={() => onRequestRemove(user)}>
              Remove User
            </button>
          ) : (
            <span />
          )}
          <div className="flex gap-3">
            <button className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button className="btn-primary" disabled={loading} onClick={handleSave}>
              {loading ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
