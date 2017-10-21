import alt from '../alt';
import AuthActions from './AuthActions';
import ApiSource from './ApiSource'

class AuthStore {
    constructor(){
        this.session = null;
        this.message = null;
        this.isPopoverOpen = false;

        this.bindListeners({
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

    handleSetSession(session) {
        this.session = session;
        this.message = null;
        this.isPopoverOpen = false;
    }

    handleFailedLogin(err){
        this.session = null;
        this.message = err ? err.message || err : err;
        if(this.message){
            this.getInstance().setPopover( {open: false, timeout: 1000} );
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