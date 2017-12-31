import alt from '../alt';
import {Intent} from "@blueprintjs/core";
import {MyToaster} from '../components/common_components';
import _ from 'lodash';

export class Message {
  constructor(s){
    this.intent = Intent.NONE;
    if ( ! _.isString(s) ) {
        if (s instanceof Error) {
            this.intent = Intent.DANGER;
        } else {
            this.intent = Intent.WARNING;
        }
    }
    this.message = ""+s;
  }

  static ensureIt(message){
    if( message instanceof Message){
      return message;
    }
    return new Message(message);
  }
}

class LogActions {
  logIt(message) {
    message = Message.ensureIt(message)
    MyToaster.show( message);
    return message;
  }
}

const logActions =  alt.createActions(LogActions);
export default logActions;



