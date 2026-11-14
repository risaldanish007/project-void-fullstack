import { cartClient } from "../api/apiClient";
import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";


const initialState = {
  items: [],
  totalQuantity: 0,
  totalPrice: 0,
  loading: false,
  error: null,
};

// Helper function to keep math consistent and prevent scientific notation bugs
const recalculateTotals = (state) => {
  state.totalQuantity = state.items.reduce(
    (total, item) => total + item.quantity,
    0
  );
  state.totalPrice = state.items.reduce(
    (total, item) => total + Number(item.price) * item.quantity,
    0
  );
};

const applyServerCart = (state, cart) => {
  state.items = (cart?.items || []).map((item) => ({
    ...item.product,
    cartItemId: item.id,
    quantity: item.quantity,
    totalItemPrice: Number(item.total_item_price),
  }));
  state.totalQuantity = cart?.total_quantity || 0;
  state.totalPrice = Number(cart?.total_price || 0);
};

export const fetchCurrentCart = createAsyncThunk(
    "cart/fetchCurrentCart",
    async(_, {rejectWithValue})  => {
        try {
            const response = await cartClient.get("/");
            return response.data
        } catch (error) {
            return rejectWithValue(
                {
                    status: error.response?.status ?? null,
                    message: error.message || "Could not load the cart",
                }
            )
        }
    }
)

export const addProductToCart = createAsyncThunk(
  "cart/addProduct",
  async ({ productId, quantity = 1 }, { rejectWithValue }) => {
    try {
      const response = await cartClient.post("/", {
        product_id: productId,
        quantity,
      });
      return response.data;
    } catch (error) {
      return rejectWithValue(
        error.response?.data || "Could not add product to cart"
      );
    }
  }
);

export const updateCartItem = createAsyncThunk(
  "cart/updateItem",
  async ({ cartItemId, quantity }, { rejectWithValue }) => {
    try {
      const response = await cartClient.patch(
        `/items/${cartItemId}/`,
        { quantity }
      );
      return response.data;
    } catch (error) {
      return rejectWithValue(
        error.response?.data || "Could not update cart item"
      );
    }
  }
);

export const deleteCartItem = createAsyncThunk(
  "cart/deleteItem",
  async (cartItemId, { rejectWithValue }) => {
    try {
      const response = await cartClient.delete(`/items/${cartItemId}/`);
      return response.data;
    } catch (error) {
      return rejectWithValue(
        error.response?.data || "Could not remove cart item"
      );
    }
  }
);

const cartSlice = createSlice({
    name: 'cart',
    initialState,
    reducers: {
        addToCart: (state, action) => {
            const newItem = action.payload;
            const existingItem = state.items.find((item) => item.id === newItem.id);

            // Keep this check for data integrity, but REMOVE the toast call
            if (existingItem && existingItem.quantity >= (newItem.countInStock || newItem.stock)) {
                return; 
            }

            if (!existingItem) {
                state.items.push({ ...newItem, quantity: 1, totalItemPrice: newItem.price });
            } else {
                existingItem.quantity++;
                existingItem.totalItemPrice += Number(newItem.price);
            }
            recalculateTotals(state);
        },
        removeFromCart: (state, action) => {
            const id = action.payload;
            const existingItem = state.items.find(item => item.id === id);

            if (!existingItem) return;

            if (existingItem.quantity === 1) {
                // Now correctly removes the item if it was the last one
                state.items = state.items.filter(item => item.id !== id);
            } else {
                existingItem.quantity--;
                existingItem.totalItemPrice -= Number(existingItem.price);
            }
            recalculateTotals(state);
        },
        clearItem: (state, action) => {
            const id = action.payload;
            state.items = state.items.filter(item => item.id !== id);
            recalculateTotals(state);
        },
        clearCart: (state) => {
            state.items = [];
            state.totalQuantity = 0;
            state.totalPrice = 0;
        },
        replaceCart: (state, action) => {
        state.items = action.payload.items || [];
        state.totalQuantity = state.items.reduce(
            (total, item) => total + item.quantity,
            0
        );
        state.totalPrice = state.items.reduce(
            (total, item) => total + Number(item.price) * item.quantity,
            0
        );
        },
    },
   extraReducers: (builder) => {
  builder
      .addCase(fetchCurrentCart.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCurrentCart.fulfilled, (state, action) => {
        state.loading = false;
        applyServerCart(state, action.payload);
      })
      .addCase(fetchCurrentCart.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(addProductToCart.pending, (state) => {
        state.error = null;
      })
      .addCase(addProductToCart.fulfilled, (state, action) => {
        applyServerCart(state, action.payload);
      })
      .addCase(addProductToCart.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(updateCartItem.fulfilled, (state, action) => {
        applyServerCart(state, action.payload);
      })
      .addCase(deleteCartItem.fulfilled, (state, action) => {
       applyServerCart(state, action.payload);
      })
      .addCase("auth/logout", (state) => {
        state.items = [];
        state.totalQuantity = 0;
        state.totalPrice = 0;
      });
  },
});

export const { addToCart, removeFromCart, clearItem, clearCart, replaceCart } = cartSlice.actions;
export default cartSlice.reducer;
