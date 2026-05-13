/**
 * API helpers for User Management.
 */

import { apiDelete, apiGet, apiPatch, apiPost } from '@/shared/lib/api';

export type UserRole = 'admin' | 'manager' | 'editor' | 'viewer';
export type ModuleAccessLevel = 'none' | 'view' | 'edit' | 'full';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  locale: string;
  is_active: boolean;
  last_login_at: string | null;
  timezone: string;
  created_at: string;
  updated_at: string;
}

export interface UserAdminUpdate {
  full_name?: string;
  role?: UserRole;
  is_active?: boolean;
  locale?: string;
}

export interface InviteUserPayload {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
}

export interface ModuleAccess {
  visible: boolean;
  access: ModuleAccessLevel;
}

export interface UserModuleAccessPayload {
  modules: Record<string, ModuleAccess>;
  custom_role_name?: string | null;
}

export interface UserProfile {
  first_name?: string | null;
  last_name?: string | null;
  phone?: string | null;
  title?: string | null;
  department?: string | null;
  date_of_commencement?: string | null;
  avatar_url?: string | null;
  notes?: string | null;
}

export async function fetchUsers(params?: {
  is_active?: boolean;
  limit?: number;
  offset?: number;
}): Promise<User[]> {
  const qs = new URLSearchParams();
  if (params?.is_active !== undefined) qs.set('is_active', String(params.is_active));
  if (params?.limit) qs.set('limit', String(params.limit));
  if (params?.offset) qs.set('offset', String(params.offset));
  const q = qs.toString();
  return apiGet<User[]>(`/v1/users/${q ? `?${q}` : ''}`);
}

export async function updateUser(id: string, data: UserAdminUpdate): Promise<User> {
  return apiPatch<User>(`/v1/users/${id}`, data);
}

export async function inviteUser(data: InviteUserPayload): Promise<User> {
  return apiPost<User>('/v1/users/auth/register/', data);
}

export async function getUserModuleAccess(userId: string): Promise<UserModuleAccessPayload> {
  return apiGet<UserModuleAccessPayload>(`/v1/users/${userId}/module-access/`);
}

export async function setUserModuleAccess(
  userId: string,
  data: UserModuleAccessPayload,
): Promise<UserModuleAccessPayload> {
  return apiPatch<UserModuleAccessPayload>(`/v1/users/${userId}/module-access/`, data);
}

export async function deleteUser(id: string): Promise<void> {
  await apiDelete(`/v1/users/${id}`);
}

export async function getUserProfile(userId: string): Promise<UserProfile> {
  return apiGet<UserProfile>(`/v1/users/${userId}/profile/`);
}

export async function setUserProfile(userId: string, data: UserProfile): Promise<UserProfile> {
  return apiPatch<UserProfile>(`/v1/users/${userId}/profile/`, data);
}

export async function requestPasswordResetForUser(email: string): Promise<void> {
  await apiPost('/v1/users/auth/forgot-password/', { email });
}
