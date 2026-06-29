import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { authService } from "../services/auth.service";
import { useAuthStore } from "../store/auth.store";

export function useLogin() {
  const { setUser, setTokens } = useAuthStore();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: authService.login,
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      navigate("/dashboard");
    },
  });
}

export function useRegister() {
  const { setUser, setTokens } = useAuthStore();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: authService.register,
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      navigate("/dashboard");
    },
  });
}

export function useLogout() {
  const { logout } = useAuthStore();
  const navigate = useNavigate();

  return () => {
    authService.logout();
    logout();
    navigate("/login");
  };
}

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: authService.getProfile,
  });
}