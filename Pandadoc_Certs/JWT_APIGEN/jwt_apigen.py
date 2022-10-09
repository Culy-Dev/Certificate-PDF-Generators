import jwt


def generate_jwt(iss, sub, exp, secret):
  """JSON Web Token in the form of {Base64url encoded header}.{Base64url encoded payload}.{Base64url encoded signature}

  Args:
      iss (str): issuer - Your API key
      sub (str): subject - Workspace identifier
      exp (int): expiration time - Timestamp (unix epoch time) until the token is valid. It is highly recommended to 
        set the exp timestamp for a short period, i.e. a matter of seconds. This way, if a token is intercepted or shared, 
        the token will only be valid for a short period of time.
      secret (str): secret key is private to you

  Returns:
      encoded_jwt: JSON Web Tokens are composed of three sections: a header, a payload (containing a claim set), and a signature. 
      The header and payload are JSON objects, which are serialized to UTF-8 bytes, then encoded using base64url encoding.
  """
  payload = {
    "iss": iss,
    "sub": sub,
    "exp": exp
  }
  secret = secret
  encoded_jwt = jwt.encode(payload, secret, algorithm="HS256")
  return encoded_jwt