import alt from '../alt';
import AuthActions from './AuthActions';
import * as Cookies from "js-cookie";

const FROM_COOKIE = 'from_cookie';
const USER_SESSION='UserSession';

const checkStatus = (response) => {
    if (response.status >= 200 && response.status < 300) {
        return response;
    } else {
        var error = new Error(response.statusText);
        error.response = response;
        throw error
    }
}

const getText = (response) => response.text()

const parseJSON = (response) => response.json()

const checkResult = (json) => {
    if (json.hasOwnProperty("result")) {
        return json.result;
    } else if (json.hasOwnProperty("error")) {
        throw new Error(json.error);
    } else {
        let error = new Error("Unknown json");
        error.response = json;
        throw error;
    }
}



class SessionStore {
    constructor(){
        this.session = null;
        this.message = null;
        this.serverInfo = null;
        this.isPopoverOpen = false;

        this.bindListeners({
          handleFetchServerInfo: AuthActions.FETCH_SERVER_INFO,
          handleSetServerInfo: AuthActions.SET_SERVER_INFO,
          handleSetPopover: AuthActions.SET_POPOVER,
          handleSetSession: AuthActions.SET_SESSION,
          handleFailedLogin: AuthActions.FAILED_LOGIN,
          handleLogIn: AuthActions.LOG_IN,
          handleLogOut: AuthActions.LOG_OUT,
        });

        this.exportPublicMethods({
          isAuthenticated: this.isAuthenticated
        });

        this.registerAsync({
            logIn() {
                return {
                    remote(state, login_msg) {
                        return post('login', login_msg);
                    },
                    success: AuthActions.setSession,
                    error: AuthActions.failedLogin,
                };
            },
            getInfo() {
                return {
                    remote(state) {
                        return post('info', {});
                    },
                    success: AuthActions.setServerInfo,
                    error: AuthActions.failedLogin,
                };
            },
            logOut(){
                return {
                    remote(store) {
                        return post('logout', {});
                    },
                    success: AuthActions.failedLogin,
                    error: AuthActions.failedLogin,
                };
            },
            setPopover(){
                return {
                    remote(store, {open, timeout}) {
                        return new Promise((success,reject)=>{
                            setTimeout(()=>success(open),timeout);
                        });
                    },
                    success: AuthActions.setPopover,
                    error: AuthActions.failedLogin,
                };
            }

        });
    }

    isAuthenticated(){
        return this.getState().session != null;
    }

    handleSetPopover(open){
        this.isPopoverOpen = open;
        if(!open){
            this.message = null;
        }
    }

    handleFetchServerInfo(info){
        this.getInstance().getInfo();
    }

    handleSetServerInfo(info){
        this.serverInfo = info;
        const remote_auth = info.isAuthenticated;
        const local_auth = this.session != null;
        if( remote_auth !== local_auth) {
            if( remote_auth ){
                this.session=FROM_COOKIE;
            }else {
                this.session = null;
                Cookies.remove(USER_SESSION);
            }
            this.isPopoverOpen = false;
        }
    }

    handleSetSession(session) {
        this.session = session;
        if(session && session !== FROM_COOKIE){
            Cookies.set(USER_SESSION, session)
        }
        this.message = null;
        this.isPopoverOpen = false;
    }

    handleFailedLogin(err){
        this.session = null;
        // Cookies.remove(USER_SESSION);
        if (err){
            this.message = err.message || err ;
            this.isPopoverOpen = true;
            this.getInstance().setPopover( {open: false, timeout: 1000} );
        }else {
            this.message = null;
        }
    }

    handleLogIn(email_passwd){
        if (!this.getInstance().isLoading()) {
            this.getInstance().logIn(email_passwd);
        }
    }

    handleLogOut(){
        if(this.getInstance().isAuthenticated()){
            this.getInstance().logOut();
        }else{
            this.handleFailedLogin(null);
        }
    }
}

const sessionStore = alt.createStore(SessionStore, 'SessionStore');

export const post = (call, msg) => {
    let headers = getHeaders({'Content-Type': 'application/json'});
    let envelope = {call, msg};
    console.log(envelope);
    return fetch('/.api/post', {
        method: 'POST',
        headers,
        credentials: 'same-origin',
        body: JSON.stringify(envelope)
    }).then(
        checkStatus
    ).then(
        parseJSON
    ).then(
        checkResult
    );
}

let getHeaders = (initParams) => {
    const sessionState = sessionStore.getState()
    let headers = {...initParams};
    if (sessionState.session != null && sessionState.session !== FROM_COOKIE) {
        headers[USER_SESSION] = sessionState.session;
    }
    return {};
};

export const get = (path) => {
    let headers = getHeaders();
    const url = '/.get/' + path;
    console.log('GET: '+url);
    return fetch(url, {
        method: 'GET',
        headers,
        credentials: 'same-origin',
    }).then(
        checkStatus
    ).then(
        getText
    );
}

export default sessionStore;