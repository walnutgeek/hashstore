import React from 'react';
import {
  Route
} from 'react-router-dom';

import classnames from 'classnames';

const Button = ({to,children,icon}) => (
  <Route render={({history}) => (
    <button
      type="button"
      className={classnames(
          'pt-button', 'pt-minimal',
          { [`pt-icon-${icon}`]: icon}
      )}
      onClick={() => { history.push(to) }}
    >
      {children}
    </button>
  )} />
)

export default Button;