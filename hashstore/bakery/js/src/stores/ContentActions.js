import alt from '../alt';
import WebPath from "../utils/WebPath";


class ContentActions {

  setPath(path) {return new WebPath(path);}

  setPathInfo(info) {return info;}

  setContent(content) {return content;}

  selectViewer(viewer) {return viewer;}
}

const contentActions =  alt.createActions(ContentActions);

export default contentActions;



