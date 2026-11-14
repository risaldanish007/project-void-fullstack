import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSelector } from 'react-redux';
import { accountsClient, ordersClient } from "../../api/apiClient";
import { toast } from 'react-toastify';
import VoidLoader from "../../styles/VoidLoader";
import ApiError from "../../components/common/ApiError";

const UserDirectory = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState("All");
  const [confirmationNode, setConfirmationNode] = useState(null);
  const [inspectUser, setInspectUser] = useState(null);
  const queryClient = useQueryClient();

  const { user: currentUser } = useSelector((state) => state.auth);

  // ── Fetch ──────────────────────────────────────────────────────────────────
  const {
    data: users,
    isLoading: usersLoading,
    isError: usersError,
    error: usersQueryError,
    refetch: refetchUsers,
  } = useQuery({
    queryKey: ["adminUsers"],
    queryFn: () => accountsClient.get("/admin/users/").then(res => res.data),
  });

  const {
    data: allOrders,
    isLoading: ordersLoading,
    isError: ordersError,
    error: ordersQueryError,
    refetch: refetchOrders,
  } = useQuery({
    queryKey: ["adminOrders"],
    queryFn: () => ordersClient.get("/admin/").then(res => res.data),
  });

  // ── Mutations ──────────────────────────────────────────────────────────────
  const banMutation = useMutation({
    mutationFn: ({ id, isBanned }) =>
      accountsClient.patch(`/admin/users/${id}/`, { is_active: isBanned }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminUsers"] });
      toast.info("SYSTEM_UPDATE: Security status modified.");
      setConfirmationNode(null);
    },
    onError: (err) => {
      const detail = err.response?.data?.detail || "Action failed.";
      toast.error(`ERROR: ${detail}`);
      setConfirmationNode(null);
    },
  });

  const roleMutation = useMutation({
    mutationFn: ({ id, is_staff }) =>
      accountsClient.patch(`/admin/users/${id}/`, { is_staff }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["adminUsers"] });
      toast.success("SYSTEM_UPDATE: Clearance levels updated.");
    },
    onError: (err) => {
      const detail = err.response?.data?.detail || "Role change failed.";
      toast.error(`ERROR: ${detail}`);
    },
  });

  // ── Filtering ──────────────────────────────────────────────────────────────
  const filteredUsers = users?.filter(user => {
    const matchesSearch =
      user.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter =
      filterType === "All" ? true :
      filterType === "Admins" ? user.role === "admin" :
      filterType === "Customers" ? user.role === "customer" :
      filterType === "Banned" ? user.status === "Banned" : true;
    return matchesSearch && matchesFilter;
  });

  if (usersLoading || ordersLoading) {
    return <VoidLoader label="Loading customer records" />;
  }
  if (usersError || ordersError) {
    return (
      <ApiError
        error={usersQueryError || ordersQueryError}
        title="Customer records unavailable"
        onRetry={() => {
          refetchUsers();
          refetchOrders();
        }}
      />
    );
  }

  return (
    <div className="animate-in fade-in duration-700 relative pb-20 px-4 md:px-0">

      {/* --- IDENTITY MANIFEST MODAL --- */}
      {inspectUser && (() => {
        // Match orders by user id (DRF returns user FK as integer)
        const userOrders = allOrders?.filter(o => o.user === inspectUser.id) || [];
        const totalSpentInr = userOrders.reduce((acc, curr) => acc + Number(curr.total_inr || 0), 0);
        const avgOrderValue = userOrders.length > 0 ? (totalSpentInr / userOrders.length).toFixed(2) : 0;
        const lastOrder = userOrders[0];
        const isSelf = inspectUser.id === currentUser?.id;

        return (
          <div className="fixed inset-0 z-[400] flex items-center justify-center bg-black/95 backdrop-blur-xl p-6">
            <div className="bg-[#0a0a0a] border border-white/10 w-full max-w-3xl rounded-[3rem] p-10 shadow-2xl relative overflow-hidden">
              <div className="flex justify-between items-start mb-10">
                <div>
                  <span className="text-cyan-500 font-mono text-[10px] tracking-[0.5em] uppercase block mb-1 font-black">Customer Account Profile</span>
                  <h2 className="text-4xl font-black italic tracking-tighter text-white uppercase">{inspectUser.name} {isSelf && "[ADMIN]"}</h2>
                  <p className="text-white/60 font-mono text-[11px] uppercase tracking-widest font-black mt-1">{inspectUser.email}</p>
                </div>
                <button onClick={() => setInspectUser(null)} className="text-white/40 hover:text-white transition-all font-mono text-[11px] font-black uppercase tracking-widest">[ Close Profile ]</button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Purchase Analytics */}
                <div className="space-y-6 bg-white/[0.02] p-6 rounded-3xl border border-white/5">
                  <h4 className="text-[11px] font-mono text-white/70 uppercase tracking-[0.4em] border-b border-white/10 pb-2 font-black">Purchase Analytics</h4>
                  <div className="space-y-5 font-mono">
                    <div>
                      <span className="text-white/40 text-[9px] font-black uppercase">Total Lifetime Value</span>
                      <p className="text-green-500 font-black italic text-2xl tracking-tighter">₹{totalSpentInr.toLocaleString()}</p>
                    </div>
                    <div className="grid grid-cols-2 gap-4 pt-2 border-t border-white/5">
                      <div>
                        <span className="text-white/40 text-[9px] font-black uppercase">AVG Order</span>
                        <p className="text-white font-black text-sm uppercase">₹{avgOrderValue}</p>
                      </div>
                      <div>
                        <span className="text-white/40 text-[9px] font-black uppercase">Orders</span>
                        <p className="text-cyan-400 font-black text-sm uppercase">{userOrders.length}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Transaction History */}
                <div className="md:col-span-2 space-y-6">
                  <h4 className="text-[11px] font-mono text-white/70 uppercase tracking-[0.4em] border-b border-white/10 pb-2 font-black">Transaction History</h4>
                  <div className="space-y-3 max-h-[250px] overflow-y-auto pr-2">
                    {userOrders.map((order, idx) => (
                      <div key={order.public_id ?? idx} className="flex justify-between items-center bg-white/5 p-4 rounded-xl border border-white/5 hover:border-white/20 transition-all group">
                        <div className="flex flex-col">
                          <span className="text-[11px] font-mono text-white font-black tracking-tighter italic">
                            Order #{String(order.public_id).slice(-8)}
                          </span>
                          <span className="text-[10px] text-white/40 font-black uppercase tracking-widest">
                            {order.created_at ? new Date(order.created_at).toLocaleDateString() : ""}
                          </span>
                        </div>
                        <div className="text-right flex items-center gap-4">
                          <span className="text-white font-black italic text-sm">₹{order.total_inr}</span>
                          <span className={`text-[8px] font-black px-2 py-1 rounded border uppercase tracking-widest 
                            ${order.status === 'delivered' ? 'text-green-500 border-green-500/20' : 'text-cyan-400 border-cyan-400/20'}`}>
                            {order.status}
                          </span>
                        </div>
                      </div>
                    ))}
                    {userOrders.length === 0 && (
                      <div className="py-10 text-center border border-dashed border-white/10 rounded-2xl bg-white/[0.01]">
                        <p className="text-white/20 font-mono text-[10px] uppercase font-black tracking-widest">No Transaction History Available</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="mt-12 pt-8 border-t border-white/10 flex flex-col md:flex-row justify-between items-center gap-6">
                <div className="flex flex-col">
                  <span className="text-white/40 text-[9px] font-mono uppercase font-black tracking-widest mb-1">Last Shipping Address</span>
                  <p className="text-white/90 text-[12px] font-black uppercase tracking-tight">
                    {lastOrder
                      ? `${lastOrder.shipping_city}, ${lastOrder.shipping_state} // Phone: ${lastOrder.shipping_phone}`
                      : "No Shipping Data Available"}
                  </p>
                </div>
                <button
                  disabled={isSelf}
                  onClick={() => { setConfirmationNode({ user: inspectUser }); setInspectUser(null); }}
                  className={`px-8 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all border
                    ${isSelf
                      ? 'opacity-10 border-white/10 text-white/10 cursor-not-allowed'
                      : 'bg-red-500/10 text-red-500 border-red-500/20 hover:bg-red-500 hover:text-white'}`}
                >
                  {isSelf ? 'Administrative Account' : inspectUser.status === 'Banned' ? 'Reactivate Account' : 'Suspend Account'}
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      {/* --- CONFIRMATION MODAL --- */}
      {confirmationNode && (
        <div className="fixed inset-0 z-[500] flex items-center justify-center bg-black/95 backdrop-blur-xl p-6">
          <div className="bg-[#0a0a0a] border border-red-500/30 w-full max-w-md rounded-[2rem] p-8 shadow-2xl text-center">
            <h2 className="text-xl font-black uppercase italic text-white mb-6">Modify Clearance?</h2>
            <div className="flex flex-col gap-3">
              <button
                onClick={() => banMutation.mutate({
                  id: confirmationNode.user.id,
                  // isBanned = what we want to set is_active to
                  // If currently Banned (is_active=false) → reactivate → is_active=true
                  // If currently Active (is_active=true) → suspend → is_active=false
                  isBanned: confirmationNode.user.status === 'Banned',
                })}
                disabled={banMutation.isPending}
                className="w-full bg-red-600 text-white py-4 rounded-xl text-[10px] font-black uppercase tracking-widest"
              >
                {banMutation.isPending ? "Processing..." : "Confirm_Action"}
              </button>
              <button onClick={() => setConfirmationNode(null)} className="w-full py-4 text-[10px] font-mono uppercase text-white/40 hover:text-white transition-colors font-black">Abort</button>
            </div>
          </div>
        </div>
      )}

      {/* --- HEADER --- */}
      <div className="max-w-6xl mx-auto">
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-8">
          <div>
            <h2 className="text-2xl font-black uppercase italic tracking-tighter text-white">User Directory</h2>
            <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mt-1">
              {filteredUsers?.length} Active Records
            </p>
          </div>
          <div className="w-full md:w-auto flex flex-col md:flex-row items-center gap-4">
            <input
              type="text"
              placeholder="SEARCH_BY_NAME_OR_EMAIL..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full md:w-64 bg-white/5 border border-white/10 rounded-xl px-5 py-3 text-[10px] font-mono text-white focus:border-cyan-500 outline-none transition-all placeholder:text-white/10"
            />
          </div>
        </header>

        <nav className="flex items-center gap-2 mb-8 bg-white/5 p-1 rounded-2xl w-fit border border-white/5">
          {["All", "Admins", "Customers", "Banned"].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-5 py-2 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all 
                ${filterType === type ? 'bg-white text-black shadow-lg' : 'text-white/40 hover:text-white hover:bg-white/5'}`}
            >
              {type}
            </button>
          ))}
        </nav>

        {/* --- DIRECTORY TABLE --- */}
        <div className="overflow-hidden border border-white/10 rounded-[2rem] bg-[#0a0a0a]/40 backdrop-blur-sm">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/5 text-[9px] font-mono text-white/30 uppercase tracking-[0.3em]">
                <th className="p-6 font-black">Identity</th>
                <th className="p-6 font-black">Fulfillment</th>
                <th className="p-6 text-right font-black">Controls</th>
              </tr>
            </thead>
            <tbody className="text-[12px] font-mono uppercase">
              {filteredUsers?.map((user) => {
                const isSelf = user.id === currentUser?.id;
                const transactionCount = user.order_count ?? 0;

                return (
                  <tr key={user.id} className={`border-b border-white/[0.03] hover:bg-white/[0.02] transition-all ${isSelf ? 'bg-cyan-500/[0.02]' : ''}`}>
                    <td className="p-6">
                      <div className="flex items-center gap-4">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-black italic text-xs border ${isSelf ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-400' : 'bg-white/5 border-white/10 text-white/40'}`}>
                          {user.name?.[0]}
                        </div>
                        <div className="flex flex-col">
                          <span className="text-white font-black tracking-tight flex items-center gap-2">
                            {user.name}
                            {isSelf && <span className="text-[8px] bg-cyan-500 text-black px-1.5 py-0.5 rounded font-black tracking-tighter">ROOT</span>}
                          </span>
                          <span className="text-[10px] text-white/20 font-black lowercase tracking-normal">{user.email}</span>
                        </div>
                      </div>
                    </td>
                    <td className="p-6">
                      <div className="flex flex-col">
                        <span className="text-white/60 font-black text-[10px] tracking-widest">{transactionCount} Dispatches</span>
                        {user.status === 'Banned' && (
                          <span className="text-[8px] text-red-500 font-black tracking-[0.2em] mt-1 animate-pulse">SUSPENDED</span>
                        )}
                      </div>
                    </td>
                    <td className="p-6 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => setInspectUser(user)}
                          className="h-9 px-4 rounded-lg text-[9px] font-black uppercase tracking-widest border border-white/10 text-white/40 hover:bg-white hover:text-black hover:border-white transition-all"
                        >
                          Inspect
                        </button>
                        <button
                          disabled={isSelf}
                          onClick={() => setConfirmationNode({ user })}
                          className={`h-9 px-4 rounded-lg text-[9px] font-black uppercase tracking-widest border transition-all
                            ${isSelf
                              ? 'opacity-10 border-transparent text-white/10'
                              : 'border-white/5 text-white/20 hover:border-yellow-500/40 hover:text-yellow-500 hover:bg-yellow-500/5'}`}
                        >
                          {user.status === 'Banned' ? 'Restore' : 'Suspend'}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default UserDirectory;
