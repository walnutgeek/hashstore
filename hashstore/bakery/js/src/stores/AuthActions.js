import alt from '../alt';
import LogActions from './LogActions'

class AuthActions {
  failedLogin(message) {
    LogActions.logIt(message);
    return message;
  }
  fetchServerInfo() {return {};}
  setServerInfo(info) {return info;}
  setSession(session) {return session;}
  logIn(email, passwd) { return {email, passwd};}
  setPopover(open) {return open;}
  logOut() {return {};}
}

const authActions =  alt.createActions(AuthActions);
export default authActions;



