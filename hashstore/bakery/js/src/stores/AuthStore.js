import alt from '../alt';
import AuthActions from './AuthActions';
import {ApiSource,FROM_COOKIE,USER_SESSION} from './ApiSource';
import * as Cookies from "js-cookie";


class AuthStore {
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

        this.registerAsync(ApiSource);
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
        Cookies.remove(USER_SESSION);
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

const authStore = alt.createStore(AuthStore, 'AuthStore');
export default authStore;