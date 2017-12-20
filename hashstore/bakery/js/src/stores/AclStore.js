
import alt from '../alt';
import AclActions from './AclActions';
import {post} from './SessionStore';
import Cake from '../utils/Cake';
import LogActions from "./LogActions";



class AclStore {
    constructor(){
        this.acls = null;

        this.bindListeners({
            handleSetAcls: AclActions.SET_ACLS,
            handleGetAcls: AclActions.GET_ACLS,
        });

        this.registerAsync({
            requestAcls() {
                return {
                    remote(state) {
                        return post('list_acls',{});
                    },
                    success: AclActions.setAcls,
                    error: LogActions.logIt,
                };
            },
        });
    }

    handleGetAcls(){
        this.acls = null;
        this.getInstance().requestAcls();
    }
    handleSetAcls(acls){
        this.acls = acls.map((a)=> (
            {
                permission: a.permission,
                cake: Cake.ensureCake(a.cake)
            }));
    }

}

const aclStore = alt.createStore(AclStore, 'AclStore');
export default aclStore;