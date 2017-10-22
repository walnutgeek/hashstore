import AuthActions from './AuthActions';

export const FROM_COOKIE = 'from_cookie';
export const USER_SESSION='UserSession';


const checkStatus = (response) => {
    if (response.status >= 200 && response.status < 300) {
        return response;
    } else {
        var error = new Error(response.statusText);
        error.response = response;
        throw error
    }
}

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

const post = (state, call, msg) => {
    let headers = {
        'Content-Type': 'application/json'
    };
    if (state.session != null && state.session !== FROM_COOKIE) {
        headers[USER_SESSION] = state.session;
    }
    return fetch('/.api/post', {
        method: 'POST',
        headers,
        credentials: 'same-origin',
        body: JSON.stringify({call, msg})
    }).then(
        checkStatus
    ).then(
        parseJSON
    ).then(
        checkResult
    );
}


export var ApiSource = {
    logIn() {
        return {
            remote(state, login_msg) {
                return post(state, 'login', login_msg);
            },
            success: AuthActions.setSession,
            error: AuthActions.failedLogin,
        };
    },
    getInfo() {
        return {
            remote(state) {
                return post(state, 'info', {});
            },
            success: AuthActions.setServerInfo,
            error: AuthActions.failedLogin,
        };
    },
    logOut(){
        return {
            remote(store) {
                return post(store, 'logout', {});
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
};

export default ApiSource;

