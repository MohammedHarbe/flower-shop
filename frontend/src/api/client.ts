import { config } from '../config'

export type ApiErrorKind = 'network' | 'not_found' | 'conflict' | 'invalid' | 'server'

export class ApiError extends Error {
  constructor(public kind: ApiErrorKind, public status?: number) {
    super(kind)
    this.name = 'ApiError'
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${config.apiUrl}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })
  } catch {
    throw new ApiError('network')
  }

  if (!response.ok) {
    const kind: ApiErrorKind =
      response.status === 404
        ? 'not_found'
        : response.status === 409
          ? 'conflict'
          : response.status === 400 || response.status === 422
            ? 'invalid'
            : 'server'
    throw new ApiError(kind, response.status)
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError('server', response.status)
  }
}
