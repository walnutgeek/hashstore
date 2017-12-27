import createHistory from 'history/createBrowserHistory';

export const history = createHistory();

export const unlisten = history.listen((location, action) => {
  // location is an object like window.location
  console.log(action, location.pathname, location.state)
});

export default history;