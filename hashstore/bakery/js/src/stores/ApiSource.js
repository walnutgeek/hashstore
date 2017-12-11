import AuthActions from './AuthActions';
import {post} from './SessionStore';

export const ApiSource = {
    getAclCakes() {
        return {
            remote(state) {
                return post('list_acl_cakes', {});
            },
            success: AuthActions.setServerInfo,
            error: AuthActions.failedLogin,
        };
    },
};

export default ApiSource;

