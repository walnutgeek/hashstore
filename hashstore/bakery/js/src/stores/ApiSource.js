import AuthActions from './AuthActions';

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
    console.log([call, msg]);
    let headers = {
        'Content-Type': 'application/json'
    };
    if (state.session != null) {
        headers['UserSession'] = state.session;
    }
    return fetch('/.api/post', {
        method: 'POST',
        headers,
        body: JSON.stringify({call, msg})
    }).then(
        checkStatus
    ).then(
        parseJSON
    ).then(
        checkResult
    );
}


var ApiSource = {
    logIn() {
        console.log('ApiSource.logIn', arguments);
        return {
            remote(state, login_msg) {
                console.log('ApiSource.logIn.remote', arguments);
                return post(state, 'login', login_msg);
            },
            success: AuthActions.setSession,
            error: AuthActions.failedLogin,
        };
    },
    logOut(){
        return {
            remote(store) {
                return post(store, 'logout', {session: store.session});
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
                })
            },
            success: AuthActions.setPopover,
            error: AuthActions.failedLogin,
        };
    },


};

export default ApiSource;

