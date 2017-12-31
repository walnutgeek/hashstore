import React from 'react';
import history from '../history'

import {
    Button, Toaster,Position
} from "@blueprintjs/core";

const createOnClicker = (OnClicker) => (
    ({to, children, ...props}) => (
        <OnClicker onClick={ () => history.push(to) } {...props}>
            {children}
        </OnClicker>
    )
);

export const ToButton = ({to, children, ...props}) => (
        <Button onClick={ () => history.push(to) } {...props}>
            {children}
        </Button>
    );

export const ToLink = ({to, children, ...props}) => (
    <a href="#" onClick={ () => history.push(to) } {...props}>
        {children}
    </a>
);

export const Icon = ({iconName}) => (
    <span className={`pt-icon pt-icon-${iconName}`}></span>);

export const MyToaster = Toaster.create({
    className: "my-toaster",
    position: Position.TOP_RIGHT,
});