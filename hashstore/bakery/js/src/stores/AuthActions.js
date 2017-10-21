import alt from '../alt';

class AuthActions {
  setPopover(open) {return open;}
  failedLogin(message) {return message;}
  setSession(session) {return session;}
  logIn(email, passwd) { return {email, passwd};}
  logOut() {return {};}
}

const authActions =  alt.createActions(AuthActions);
export default authActions;



