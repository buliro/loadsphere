export type AuthUser = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
};

export type AuthSession = {
  authenticated: boolean;
  user: AuthUser | null;
};

export type RegisterPayload = {
  email: string;
  password1: string;
  password2: string;
  first_name: string;
  last_name: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};
