"""Path and OD classes are used either by Railway or Roadway networks."""


class BasePath(object):

    def get_links(self):
        return self.links

    def get_id(self):
        return self.id

    def get_path(self):
        return self.path

    def get_gauge(self):
        return self.gauge

    def calc_distance(self, network_links):
        """Takes a dictionary with all network links and sum distance of od
        links to calculate distance of od pair."""

        # init distance with zero
        dist = 0

        # iterate through od used links adding its distance to od distance
        for od_link in self.links:

            try:
                dist += network_links[od_link][self.gauge].get_dist()

            except:
                print od_link, self.gauge, "is missing in network links list!",
                print "od pair: ", self.id

        return dist

    def _create_links_list(self):
        """Create list with all links used by OD path."""

        # create emtpy dict to store links
        links = []

        # check there is a path
        if self.path_nodes:

            # iterate through path nodes creating links
            for i in xrange(len(self.path_nodes) - 1):

                # take two consecutive nodes
                node_a = int(self.path_nodes[i])
                node_b = int(self.path_nodes[i + 1])

                # create link, putting first the node with less value
                if node_a < node_b:
                    link_id = "-".join([str(node_a), str(node_b)])

                else:
                    link_id = "-".join([str(node_b), str(node_a)])

                # add the link to the dict
                links.append(link_id)

        return links

    def _get_path_nodes(self):
        """Create list with all nodes in OD path."""

        # check if OD has no path (when O == D)
        if self.path and self.nodes[0] != self.nodes[1]:

            # if possible, split path in nodes
            try:
                return [int(i) for i in self.path.split("-")]

            # where path doesn't have "-" is not a valid path
            except:
                return None

        else:
            return None

    def _get_safe_id(self, id):
        """Return id properly built.

        ODs ids must be always created with number of lowest numeration node
        first and number of highest numeration node last.

            Right: 10-25
            Wrong: 25-10

        This method assures proper identification of od pairs."""

        nodes = [int(i) for i in id.split("-")]

        # check if first node is less than second one
        if nodes[0] < nodes[1]:
            id_checked = str(nodes[0]) + "-" + str(nodes[1])

        # change order of nodes in the id, if second node is less than first
        else:
            id_checked = str(nodes[1]) + "-" + str(nodes[0])

        return id_checked


class Path(BasePath):

    """Represents a railway or roadway path.

    Roadway paths are considered to have unique gauge."""

    def __init__(self, id, path, gauge):
        self.id = self._get_safe_id(id)
        self.path = path
        self.gauge = gauge
        self.nodes = [int(i) for i in self.id.split("-")]

        # path properties
        self.path_nodes = self._get_path_nodes()
        self.links = self._create_links_list()

    def __repr__(self):
        return "OD: " + self.id.ljust(10) + \
               "Path: " + self.path.ljust(70) + \
               "Gauge: " + str(self.gauge)


class OD(BasePath):

    """Represents an od pair in a railway or roadway network.

    It carries tons of freight and has path, gauge and distance. Roadway od
    pairs are considered to have unique gauge."""

    NF = "{:,.1f}"
    FIELDS = ["id_od", "gauge", "distance", "original ton", "derived ton",
              "ton", "railway_category", "path", "id_lowest_link",
              "ton_lowest_link", "deposit_cost", "short_freight_cost",
              "immo_value_cost"]

    def __init__(self, id, ton, path=None, gauge=None, dist=None,
                 rail_category=None):

        # identification properties
        self.id = self._get_safe_id(id)
        self.nodes = [int(i) for i in self.id.split("-")]

        # path properties
        self.path = path
        self.path_nodes = self._get_path_nodes()
        self.gauge = gauge
        self.dist = dist
        self.links = self._create_links_list()

        # traffic properties
        self.original_ton = ton
        self.derived_ton = 0.0
        self.rail_category = rail_category
        self.lowest_link = None

        # cost properties
        self.deposit_cost = None
        self.short_freight_cost = None
        self.immo_value_cost = None

    def __repr__(self):
        return "OD: " + self.id.ljust(10) + \
               "Ton: " + self.NF.format(self.get_ton()).ljust(15) + \
               "Gauge:" + str(self.gauge).ljust(15) + \
               "Distance:" + str(self.dist).ljust(15) + \
               "Category:" + str(self.rail_category)

    def __lt__(self, other):
        return self.get_ton() < other.get_ton()

    # PUBLIC
    # GET methods
    def get_original_ton(self):
        """Get tons that are originally transported by the transport mode."""
        return self.original_ton

    def get_derived_ton(self):
        """Get tons that are derived from other freight transport mode."""
        return self.derived_ton

    def get_ton(self):
        """Get total tons of od pair, original and derived freight."""
        return self.get_original_ton() + self.get_derived_ton()

    def get_attributes(self):
        return [self.id, self.gauge, self.dist, self.get_original_ton(),
                self.get_derived_ton(), self.get_ton(), self.get_category(),
                self.path, self.get_lowest_link_id(),
                self.get_lowest_link_scale(), self.get_deposit_cost(),
                self.get_short_freight_cost(), self.get_immo_value_cost()]

    def get_dist(self):
        return self.dist

    def get_category(self):
        return self.rail_category

    def get_lowest_link_scale(self):
        """Returns the tons passing through the lowest link used by OD pair.

        It is a mesure used to calculate the frequency that train services can
        have for the OD pair, taking into account the worst part of the path,
        in terms of the scale reached."""

        if self.lowest_link:
            return self.lowest_link.get_ton()

        else:
            return None

    def get_lowest_link_id(self):
        """Returns the tons passing through the lowest link used by OD pair.

        It is a mesure used to calculate the frequency that train services can
        have for the OD pair, taking into account the worst part of the path,
        in terms of the scale reached."""

        if self.lowest_link:
            return self.lowest_link.get_id()

        else:
            return None

    def get_deposit_cost(self):
        return self.deposit_cost

    def get_short_freight_cost(self):
        return self.short_freight_cost

    def get_immo_value_cost(self):
        return self.immo_value_cost

    def calc_distance(self, network_links):
        self.dist = super(OD, self).calc_distance(network_links)

    # SET and ADD methods
    def add_original_ton(self, ton):
        """Add original tons to OD pair."""
        self.original_ton += ton

    def derive_ton(self, other, coeff=1.0):
        """Derive tons to another freight transport mode.

        It derives tons to an OD pair object coming from another transport mode
        but with the same id. Only original tons of the od pair are subject to
        derivation coefficient (coeff), while previously derivated tons are
        just returned completely

        Args:
            other: OD object from another transport mode that will receive
                derived tons from self OD object.
            coeff (opt): Coefficient of tons that will be derived. The default
                is to derive all tons (1.0)

        Raise:
            DerivationError: Trying to derive tons to an other od pair with
                different id will raise an error. Derivation must occur with an
                od pair with the same origin and destination (ie, same id)
        """

        # check od pairs have same id and category
        msg = "OD pairs are different: {} != {}".format(self.get_id(),
                                                        other.get_id())
        assert (self.get_id() == other.get_id() and
                self.get_category() == other.get_category()), msg

        # calculate original tons from both od pairs
        self_original_ton = self.get_original_ton() + other.get_derived_ton()

        # calculate tons should be derived
        ton_should_be_derived = self_original_ton * coeff
        ton_already_derived = other.get_derived_ton()
        ton_to_derive = ton_should_be_derived - ton_already_derived

        # get tons to be returned (derived from "other" previously)
        ton_to_return = self.get_derived_ton()

        # remove tons from self od pair
        self.original_ton -= ton_to_derive
        self.derived_ton -= ton_to_return

        # add tons to other od pair
        other.derived_ton += ton_to_derive
        other.original_ton += ton_to_return

        return (ton_to_derive, ton_to_return)

    def set_path(self, path, gauge):
        """Take a path and gauge and set it to the od pair."""

        # set data members
        self.path = path
        self.gauge = gauge

        # get path nodes from new path and create links dictionary
        self.path_nodes = self._get_path_nodes()
        self.links = self._create_links_list()

    def set_category(self, category_od):
        self.rail_category = category_od

    def set_lowest_scale_link(self, link):
        self.lowest_link = link

    def set_deposit_cost(self, deposit_cost):
        self.deposit_cost = deposit_cost

    def set_short_freight_cost(self, short_freight_cost):
        self.short_freight_cost = short_freight_cost

    def set_immo_value_cost(self, immo_value_cost):
        self.immo_value_cost = immo_value_cost

    # BOOL methods
    def has_declared_path(self):
        """Has a path data member, even if its a "not found" one."""
        return bool(self.path and self.gauge)

    def is_intrazone(self):
        """Check if origin = destination."""
        return len(self.nodes) == 2 and self.nodes[0] == self.nodes[1]

    def has_operable_path(self):
        """Has a positive path that can be operated."""
        return self.has_declared_path() and self.path_nodes
