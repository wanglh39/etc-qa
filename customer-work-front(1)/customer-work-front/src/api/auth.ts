import request from '@/utils/request'

export interface LoginParams {
  username: string
  password: string
}

export interface LoginResult {
  access_token: string
  token_type: string
  role: string
  dept: string
}

export function login(params: LoginParams): Promise<LoginResult> {
  return request.post('/auth/login', params).then((res) => res.data)
}
