import React from 'react';
import {
  Route
} from 'react-router-dom';

import {Button} from "@blueprintjs/core";


const ToButton = ({to, children, ...props}) => (
  <Route render={({history}) => (
    <Button onClick={ ()=> history.push(to) } {...props}>
      {children}
    </Button>
  )} />
)

export default ToButton;