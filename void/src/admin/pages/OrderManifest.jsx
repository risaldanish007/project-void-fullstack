import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ordersClient } from "../../api/apiClient";
import { toast } from 'react-toastify';
import VoidLoader from "../../styles/VoidLoader";
import ApiError from "../../components/common/ApiError";
import AdminPageHeader from "../components/AdminPageHeader";

// Map DRF order status values to the UI's display labels and select values.
// DRF Status choices: pending_payment, placed, processing, shipped, delivered, cancelled
const STATUS_DISPLAY = {
  pending_payment: "Pending",
  placed: "Pending",
  processing: "Pending",
  shipped: "Deployed",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

// What the select dropdown sends → Django accepts any of these via AdminOrderStatusSerializer
const UI_STATUSES = ["Pending", "Deployed", "Delivered", "Cancelled"];

const getStatusColor = (uiStatus) => {
  const s = uiStatus?.toLowerCase();
  if (s === 'delivered') return 'text-green-500 border-green-500/20 bg-green-500/5';
  if (s === 'deployed') return 'text-cyan-400 border-cyan-400/20 bg-cyan-400/5';
  if (s === 'cancelled') return 'text-red-500 border-red-500/20 bg-red-500/5';
  return 'text-yellow-500 border-yellow-500/20 bg-yellow-500/5';
};

// Normalise a DRF order object to the shape the UI expects.
const normaliseOrder = (o) => ({
  ...o,
  // Use public_id (UUID) as the display/key identifier
  id: o.public_id,
  customerName: o.customer_name,
  customerEmail: o.customer_email,
  // Map to UI status label
  uiStatus: STATUS_DISPLAY[o.status] || "Pending",
  // Single total field for display (INR)
  total: o.total_inr,
  date: o.created_at,
  shippingAddress: {
    address: o.shipping_address,
    city: o.shipping_city,
    state: o.shipping_state,
    zip: o.shipping_postal_code,
    phone: o.shipping_phone,
  },
  items: (o.items || []).map(item => ({
    id: item.id,
    name: item.product_name,
    quantity: item.quantity,
    price: item.unit_price_inr,
  })),
});

const OrderManifest = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [timeFilter, setTimeFilter] = useState("All Time");
  const [selectedOrder, setSelectedOrder] = useState(null);
  const queryClient = useQueryClient();

  // ── Fetch ──────────────────────────────────────────────────────────────────
  const { data: orders, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["adminOrders"],
    queryFn: async () => {
      const response = await ordersClient.get("/admin/");
      return response.data.map(normaliseOrder);
    },
  });

  // ── Filtering ──────────────────────────────────────────────────────────────
  const filteredOrders = orders?.filter(order => {
    const term = searchTerm.toLowerCase();
    const matchesSearch =
      order.id?.toString().toLowerCase().includes(term) ||
      order.customerName?.toLowerCase().includes(term) ||
      order.customerEmail?.toLowerCase().includes(term);

    const matchesStatus = statusFilter === "All" || order.uiStatus === statusFilter;

    const orderDate = new Date(order.date);
    const today = new Date();
    const isToday = orderDate.toDateString() === today.toDateString();
    const isThisWeek = (today - orderDate) / (1000 * 60 * 60 * 24) <= 7;

    const matchesTime =
      timeFilter === "All Time" ? true :
      timeFilter === "Today" ? isToday :
      timeFilter === "This Week" ? isThisWeek : true;

    return matchesSearch && matchesStatus && matchesTime;
  });

  // ── Status mutation ────────────────────────────────────────────────────────
  const statusMutation = useMutation({
    mutationFn: async ({ orderId, newStatus }) => {
      return ordersClient.patch(`/admin/${orderId}/`, { status: newStatus });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminOrders"] });
      toast.info("Transaction status successfully updated.");
    },
    onError: (err) => {
      const detail = err.response?.data?.detail || "Status update failed.";
      toast.error(`ERROR: ${detail}`);
    },
  });

  if (isLoading) return <VoidLoader label="Loading orders" />;
  if (isError) {
    return <ApiError error={error} title="Orders unavailable" onRetry={refetch} />;
  }

  return (
    <div className="admin-page animate-in fade-in duration-700 relative pb-16 font-sans">

      {/* --- ORDER DETAIL MANIFEST --- */}
      {selectedOrder && (
        <div className="fixed inset-0 z-[400] flex items-center justify-center bg-black/95 backdrop-blur-xl p-6">
          <div className="admin-modal-panel bg-[#0f0f0f] border border-white/10 w-full max-w-3xl rounded-2xl p-5 sm:p-8 shadow-2xl relative">
            <div className="flex justify-between items-start mb-10 border-b border-white/5 pb-6">
              <div>
                <span className="text-cyan-400 font-bold text-[10px] tracking-[0.3em] uppercase block mb-1">Detailed Order Manifest</span>
                <h2 className="text-3xl font-bold italic tracking-tighter text-white uppercase">Invoice #{String(selectedOrder.id).slice(-8)}</h2>
              </div>
              <button onClick={() => setSelectedOrder(null)} className="text-white/40 hover:text-white transition-all text-[10px] font-bold uppercase tracking-widest border border-white/10 px-4 py-2 rounded-lg">Close Manifest</button>
            </div>

            <div className="grid md:grid-cols-2 gap-12">
              <div className="space-y-6">
                <h4 className="text-[10px] text-white/40 uppercase tracking-[0.2em] font-bold border-b border-white/5 pb-2">Customer Profile</h4>
                <div className="space-y-4">
                  <p className="text-white text-xl font-bold italic tracking-tight uppercase">{selectedOrder.customerName}</p>
                  <p className="text-white/60 text-xs font-medium lowercase">{selectedOrder.customerEmail}</p>
                  <div className="pt-4 border-t border-white/5">
                    <p className="text-[9px] text-white/30 uppercase mb-2 font-bold tracking-widest">Delivery Address</p>
                    <p className="text-white/80 text-xs leading-relaxed uppercase font-bold tracking-wider">
                      {selectedOrder.shippingAddress.address}<br/>
                      {selectedOrder.shippingAddress.city}, {selectedOrder.shippingAddress.state} {selectedOrder.shippingAddress.zip}
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-6">
                <h4 className="text-[10px] text-white/40 uppercase tracking-[0.2em] font-bold border-b border-white/5 pb-2">Inventory Payload</h4>
                <div className="space-y-3 max-h-[200px] overflow-y-auto pr-2">
                  {selectedOrder.items.map((item, idx) => (
                    <div key={item.id ?? idx} className="flex items-center gap-4 bg-white/[0.03] p-3 rounded-xl border border-white/5">
                      <div className="flex-1">
                        <p className="text-white text-[10px] font-bold uppercase tracking-widest">{item.name}</p>
                        <p className="text-white/30 text-[9px] font-bold uppercase">Quantity: {item.quantity} // Rate: ₹{item.price}</p>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="pt-6 border-t border-white/5 flex justify-between items-end">
                  <span className="text-white/30 text-[10px] uppercase tracking-[0.2em] font-bold">Total Liability</span>
                  <span className="text-3xl font-bold italic text-white tracking-tighter">₹{selectedOrder.total}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --- HEADER & FILTERS --- */}
      <div className="mb-6 flex flex-col gap-5">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <AdminPageHeader title="Orders" description={`${filteredOrders?.length ?? 0} orders match the current filters.`} />
          <input
            type="text"
            placeholder="Search by ID or Customer Name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full md:w-80 bg-white/5 border border-white/10 rounded-2xl px-6 py-4 text-xs text-white focus:border-white/30 outline-none transition-all placeholder:text-white/20 italic"
          />
        </div>

        <div className="flex flex-wrap gap-4 border-t border-white/5 pt-8">
          <div className="flex gap-2">
            {["All", ...UI_STATUSES].map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-5 py-2.5 rounded-full text-[10px] font-bold uppercase tracking-widest transition-all border 
                  ${statusFilter === s ? 'bg-white border-white text-black shadow-lg' : 'bg-white/5 border-white/10 text-white/50 hover:text-white'}`}
              >
                {s}
              </button>
            ))}
          </div>
          <div className="w-[1px] h-8 bg-white/10 hidden md:block" />
          <div className="flex gap-2">
            {["All Time", "Today", "This Week"].map((time) => (
              <button
                key={time}
                onClick={() => setTimeFilter(time)}
                className={`px-5 py-2.5 rounded-full text-[10px] font-bold uppercase tracking-widest transition-all border 
                  ${timeFilter === time ? 'bg-white border-white text-black' : 'bg-white/5 border-white/10 text-white/40 hover:text-white'}`}
              >
                {time}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* --- ORDER TABLE --- */}
      <div className="admin-table-scroll">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/10 text-[10px] text-white/40 uppercase tracking-[0.2em] bg-white/[0.02]">
              <th className="p-7 font-bold">Transaction ID</th>
              <th className="p-7 font-bold">Customer Profile</th>
              <th className="p-7 font-bold">Gross Amount</th>
              <th className="p-7 font-bold">Fulfillment Status</th>
              <th className="p-7 text-right font-bold">Administrative Options</th>
            </tr>
          </thead>
          <tbody className="text-xs uppercase">
            {filteredOrders?.map((order) => (
              <tr key={order.id} className="border-b border-white/[0.05] hover:bg-white/[0.03] transition-all group">
                <td className="p-7 text-white font-bold italic tracking-tighter text-base">
                  #{String(order.id).slice(-8)}
                </td>
                <td className="p-7">
                  <div className="flex flex-col">
                    <span className="text-white font-bold tracking-tight">{order.customerName}</span>
                    <span className="text-[10px] text-white/40 font-medium lowercase mt-1">{order.customerEmail}</span>
                  </div>
                </td>
                <td className="p-7 text-white font-bold italic text-sm">₹{order.total}</td>
                <td className="p-7">
                  <span className={`px-4 py-1.5 rounded-lg text-[9px] font-bold tracking-widest border transition-colors ${getStatusColor(order.uiStatus)}`}>
                    {order.uiStatus}
                  </span>
                </td>
                <td className="p-7 text-right">
                  <div className="flex justify-end gap-3">
                    <button
                      onClick={() => setSelectedOrder(order)}
                      className="text-[10px] font-bold uppercase tracking-widest border border-white/10 px-5 py-3 rounded-xl text-white/60 hover:bg-white hover:text-black transition-all"
                    >
                      Manifest
                    </button>
                    <select
                      value={order.uiStatus}
                      onChange={(e) => statusMutation.mutate({ orderId: order.id, newStatus: e.target.value })}
                      className="bg-[#111] border border-white/10 text-white text-[10px] font-bold uppercase tracking-widest rounded-xl px-4 py-3 outline-none focus:border-white/30 cursor-pointer hover:bg-white/5 transition-all"
                    >
                      {UI_STATUSES.map(s => (
                        <option key={s} value={s} className="bg-[#0a0a0a] text-white">{s}</option>
                      ))}
                    </select>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default OrderManifest;
