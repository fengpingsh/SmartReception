
CXX		:= g++
CC		:= gcc


#Q_              := @
ifndef BSTM_SDK_LIB
BSTM_SDK_LIB := /home/fengping/Downloads/iotivity/out/linux/x86_64/release/
BSTM_SDK_INC := -I/home/fengping/Downloads/iotivity/out/linux/x86_64/release/include/resource/ \
	-I/home/fengping/Downloads/iotivity/out/linux/x86_64/release/include/c_common/
endif

VERNUM = $(shell cat VERINFO |awk '{print $$2}' | cut -b 2- )
DVRGW_SUFFIX = $(VERNUM)

# source file dir
INC_PATH     = ${BSTM_SDK_INC}
SRC_PATH     = src
OBJ_PATH     = .obj
BIN_PATH     = bin
BIN_NAME     = facesensor
DES_PATH     = OUT



# INC DIRS.

INCDIRS +=	\
	${BSTM_SDK_INC}


            
CFLAGS	= -g -ggdb -MMD -Wall -W -std=c++11
#CFLAGS += -DUCLIBC_VERSION="libuClibc-0.9.29.so"
CFLAGS += -O2 -DSOCKLEN_T=socklen_t -D_LARGEFILE_SOURCE=1 -D_FILE_OFFSET_BITS=64 -DBSD=1

#ifneq ($(USE_BSTM_AFM),yes)
#CFLAGS += -DUSE_BSTM_AFM
#endif

CFLAGS += -DWITH_POSIX

THIRDPARTY_LIBS	= \
		-L${BSTM_SDK_LIB}/	\
		-lcoap -lconnectivity_abstraction -loctbstack -loc -loc_logger

#-lbstm_resmgrapi -lbstm_appagent -lbstm_sdkdev	\

# If you use other libraries, add them to LDFLAGS below.
LDFLAGS = \
		$(THIRDPARTY_LIBS)

# System lib path
LDFLAGS +=	\
		-lcpp_redis -lpthread -ltacopie

# source file obj
MAIN_OBJS    = $(patsubst $(SRC_PATH)/%.cpp, $(OBJ_PATH)/%.o, $(wildcard $(SRC_PATH)/*.cpp))

# target
TGT_BIN = $(BIN_NAME).$(DVRGW_SUFFIX)

# make all modules.
all: DEPENDS $(TGT_BIN)

DEPENDS:
	$(Q_)echo "::: compiling depends ..."
	mkdir -p $(OBJ_PATH)

$(TGT_BIN): $(MAIN_OBJS)
	$(Q_)echo ">>> compiling $(TGT_BIN) ..."
	$(Q_)$(CXX) -o $(BIN_PATH)/$@ $^ $(LDFLAGS)
	$(Q_)(cd $(BIN_PATH) && ln -sf $(TGT_BIN) $(BIN_NAME))
	
# src --> obj.
$(OBJ_PATH)/%.o: $(SRC_PATH)/%.cpp
	$(Q_)echo ">>> compiling $< ..."
	$(Q_)$(CXX) $(CFLAGS) $(INCDIRS) -c $< -o $@

install:
	@rm -rf $(BSTM_INSTALL_ROOT)/bin/$(TGT_BIN)
	@rm -rf $(BSTM_INSTALL_ROOT)/bin/$(BIN_NAME)
	@cp -rf bin/* $(BSTM_INSTALL_ROOT)/bin/.
	
clean:
	$(Q_)echo ":: clean $(BIN_NAME)"
	$(Q_)(cd $(BIN_PATH) && rm -f $(BIN_NAME) $(TGT_BIN))
	$(Q_)rm -f $(OBJ_PATH)/*.[do]
	$(Q_)rm $(DES_PATH) -fr

