import client from './client';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  username: string;
  role: string;
  display_name: string | null;
}

export interface UserInfo {
  id: string;
  username: string;
  role: string;
  display_name: string | null;
  enabled: boolean;
}

export const authApi = {
  login: (data: LoginRequest) =>
    client.post<TokenResponse>('/auth/login', data, { skipErrorMessage: true }).then((r) => r.data),

  getMe: () =>
    client.get<UserInfo>('/auth/me').then((r) => r.data),

  changePassword: (oldPassword: string, newPassword: string) =>
    client.post('/auth/change-password', null, {
      params: { old_password: oldPassword, new_password: newPassword },
    }),
};
