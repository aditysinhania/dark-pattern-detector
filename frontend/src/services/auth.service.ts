import api from "./api";
import type {
  ApiResponse,
  TokenResponse,
  RegisterResponse,
  User,
  UserProfile,
} from "../types";

export const authService = {
  async register(data: {
    email: string;
    password: string;
    full_name: string;
  }): Promise<RegisterResponse> {
    const res = await api.post<ApiResponse<RegisterResponse>>(
      "/auth/register",
      data
    );
    return res.data.data;
  },

  async login(data: {
    email: string;
    password: string;
  }): Promise<TokenResponse> {
    const res = await api.post<ApiResponse<TokenResponse>>(
      "/auth/login",
      data
    );
    return res.data.data;
  },

  async getMe(): Promise<User> {
    const res = await api.get<ApiResponse<User>>("/auth/me");
    return res.data.data;
  },

  async getProfile(): Promise<UserProfile> {
    const res = await api.get<ApiResponse<UserProfile>>("/users/me");
    return res.data.data;
  },

  async updateProfile(data: {
    full_name?: string;
    email?: string;
  }): Promise<User> {
    const res = await api.patch<ApiResponse<User>>("/users/me", data);
    return res.data.data;
  },

  async changePassword(data: {
    current_password: string;
    new_password: string;
  }): Promise<void> {
    await api.post("/auth/change-password", data);
  },

  logout(): void {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },
};