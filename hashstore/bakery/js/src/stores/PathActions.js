import alt from '../alt';
import WebPath from "../utils/WebPath";

class PathActions {
  setPath(path) {return new WebPath(path);}
  setPathInfo(info) {return info;}
}

const pathActions =  alt.createActions(PathActions);

export default pathActions;



