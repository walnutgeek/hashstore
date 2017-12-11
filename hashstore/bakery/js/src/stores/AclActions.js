import alt from '../alt';
import WebPath from "../utils/WebPath";

class AclActions {
    getAcls() {return {};}
    setAcls(acls) {return acls;}
}

const aclActions =  alt.createActions(AclActions);

export default aclActions;



